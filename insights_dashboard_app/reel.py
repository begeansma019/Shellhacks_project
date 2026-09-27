import asyncio
import random
import flet as ft


# ============================================================
# VISUAL CONFIGURATION
# ============================================================

DIGIT_WIDTH = 24
DIGIT_HEIGHT = 42
FONT_SIZE = 30

BACKGROUND = "#0F0F0F"
CARD_BACKGROUND = "#181818"

TEXT_COLOR = "#F1F1F1"
SECONDARY_TEXT = "#AAAAAA"


# ============================================================
# REEL CONFIGURATION
# ============================================================
#
# Each digit has only 30 cells:
#
# Cycle 0:
# 0 1 2 3 4 5 6 7 8 9
#
# Cycle 1:
# 0 1 2 3 4 5 6 7 8 9   <- resting position
#
# Cycle 2:
# 0 1 2 3 4 5 6 7 8 9
#
# This is enough room to animate any 0-9 transition while
# keeping the Flet control tree very small.
# ============================================================

REEL_CYCLES = 3
CENTER_CYCLE = 1


# ============================================================
# SMOOTH ANIMATION CONFIGURATION
# ============================================================

# Minimum duration for any changed digit.
BASE_DURATION = 200

# Additional duration for every digit cell traveled.
PER_STEP_DURATION = 28

# Smooth acceleration + smooth deceleration.
ANIMATION_CURVE = ft.AnimationCurve.EASE_IN_OUT

# Flet dispatches the scroll animation to Flutter.
# Give the client a small safety margin before resetting reels.
ANIMATION_SAFETY_MS = 100

# Newly rebuilt scroll controls need one browser paint/mount window
# before scroll_to() is dispatched on hosted Flet web sessions.
REEL_MOUNT_SETTLE_SECONDS = 0.10


# ============================================================
# DIGIT CELL
# ============================================================

def create_digit_cell(
    value: int,
    *,
    digit_width: int = DIGIT_WIDTH,
    digit_height: int = DIGIT_HEIGHT,
    font_size: int = FONT_SIZE,
    text_color: str = TEXT_COLOR,
    font_weight: ft.FontWeight = ft.FontWeight.W_500,
) -> ft.Container:
    return ft.Container(
        width=digit_width,
        height=digit_height,
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            str(value),
            size=font_size,
            weight=font_weight,
            color=text_color,
            no_wrap=True,
        ),
    )


# ============================================================
# INDIVIDUAL DIGIT REEL
# ============================================================

class DigitReel:
    """
    One independently scrollable digit.

    Every visible digit has its own Column and its own
    scroll position.
    """

    def __init__(
        self,
        value: int,
        *,
        digit_width: int = DIGIT_WIDTH,
        digit_height: int = DIGIT_HEIGHT,
        font_size: int = FONT_SIZE,
        text_color: str = TEXT_COLOR,
        font_weight: ft.FontWeight = ft.FontWeight.W_500,
    ):

        self.value = value
        self.digit_height = digit_height

        # Start on the middle copy of the digit.
        self.index = (
            CENTER_CYCLE * 10
            + value
        )

        # ----------------------------------------------------
        # Only 30 controls total per digit.
        # ----------------------------------------------------

        cells = [
            create_digit_cell(
                i % 10,
                digit_width=digit_width,
                digit_height=digit_height,
                font_size=font_size,
                text_color=text_color,
                font_weight=font_weight,
            )
            for i in range(REEL_CYCLES * 10)
        ]

        # ----------------------------------------------------
        # Scrollable reel
        # ----------------------------------------------------

        self.reel = ft.Column(
            width=digit_width,
            height=digit_height,

            spacing=0,

            scroll=ft.ScrollMode.HIDDEN,

            # Required for scroll_to().
            auto_scroll=False,

            controls=cells,
        )

        # ----------------------------------------------------
        # One-digit viewport
        # ----------------------------------------------------

        self.control = ft.Container(
            width=digit_width,
            height=digit_height,

            clip_behavior=ft.ClipBehavior.HARD_EDGE,

            content=ft.Stack(
                width=digit_width,
                height=digit_height,
                controls=[
                    self.reel,

                    # This transparent top layer captures all
                    # manual scrolling without affecting scroll_to().
                    ft.GestureDetector(
                        width=digit_width,
                        height=digit_height,
                        on_vertical_drag_update=lambda e: None,
                        on_scroll=lambda e: None,
                        content=ft.Container(
                            width=digit_width,
                            height=digit_height,
                            bgcolor=ft.Colors.TRANSPARENT,
                        ),
                    ),
                ],
            ),
        )

    # ========================================================
    # INITIAL POSITION
    # ========================================================

    async def initialize(self):
        """
        Position reel on its initial digit with no animation.
        """

        await self.reel.scroll_to(
            offset=self.index * self.digit_height,
            duration=0,
        )

    # ========================================================
    # ROLL TO NEW DIGIT
    # ========================================================

    def animation_duration_to(
        self,
        new_value: int,
        increasing: bool,
    ) -> int:
        if new_value == self.value:
            return 0

        if increasing:
            steps = (
                new_value - self.value
            ) % 10
        else:
            steps = (
                self.value - new_value
            ) % 10

        return BASE_DURATION + steps * PER_STEP_DURATION

    async def roll_to(
        self,
        new_value: int,
        increasing: bool,
    ) -> int:
        """
        Animate this digit to a new value.

        Returns the requested animation duration.
        """

        # Unchanged digits remain completely stationary.
        if new_value == self.value:
            return 0

        old_value = self.value

        # ----------------------------------------------------
        # Determine how many cells THIS reel must travel.
        # ----------------------------------------------------

        if increasing:

            # Examples:
            #
            # 3 -> 5 = 2
            # 8 -> 2 = 4
            #
            # 8, 9, 0, 1, 2
            #
            steps = (
                new_value - old_value
            ) % 10

            target_index = (
                self.index + steps
            )

        else:

            steps = (
                old_value - new_value
            ) % 10

            target_index = (
                self.index - steps
            )

        if steps == 0:
            return 0

        # ----------------------------------------------------
        # Smooth independent duration
        # ----------------------------------------------------
        #
        # 1 step = 228 ms
        # 2 steps = 256 ms
        # 3 steps = 284 ms
        # 4 steps = 312 ms
        # ...
        #
        # Farther reels still move slightly longer, but not so
        # differently that the counter feels disconnected.
        # ----------------------------------------------------

        duration = self.animation_duration_to(
            new_value,
            increasing,
        )

        # Save logical destination.
        self.value = new_value
        self.index = target_index

        # ----------------------------------------------------
        # Actual animated scrolling.
        # ----------------------------------------------------

        await self.reel.scroll_to(
            offset=target_index * self.digit_height,
            duration=duration,
            curve=ANIMATION_CURVE,
        )

        return duration

    # ========================================================
    # INVISIBLE RECENTER
    # ========================================================

    async def recenter(self):
        """
        Move the reel back to the identical digit in the
        center cycle without animation.

        Example:

        Cycle 2:
            5
            ↑ currently displayed

        becomes:

        Cycle 1:
            5
            ↑ same visible digit

        The viewer sees no value change.
        """

        center_index = (
            CENTER_CYCLE * 10
            + self.value
        )

        if self.index == center_index:
            return

        await self.reel.scroll_to(
            offset=center_index * self.digit_height,
            duration=0,
        )

        self.index = center_index


# ============================================================
# REUSABLE MULTI-DIGIT REEL
# ============================================================

class RollingNumber:
    """A retained multi-digit value driven by ``DigitReel`` controls."""

    def __init__(
        self,
        page: ft.Page,
        value: int,
        *,
        digit_width: int = DIGIT_WIDTH,
        digit_height: int = DIGIT_HEIGHT,
        font_size: int = FONT_SIZE,
        text_color: str = TEXT_COLOR,
        font_weight: ft.FontWeight = ft.FontWeight.W_500,
    ):
        self.page = page
        self.value = value
        self.digit_width = digit_width
        self.digit_height = digit_height
        self.font_size = font_size
        self.text_color = text_color
        self.font_weight = font_weight

        self.reels: list[DigitReel] = []
        self._animation_running = False
        self._pending_value: int | None = None
        self._pending_transition = None

        self.row = ft.Row(
            spacing=0,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.control = ft.Container(
            height=digit_height,
            opacity=0,
            alignment=ft.Alignment.CENTER,
            content=self.row,
        )

        self._build(value)

    def _build(self, value: int):
        raw_number = str(value)
        self.reels = [
            DigitReel(
                int(character),
                digit_width=self.digit_width,
                digit_height=self.digit_height,
                font_size=self.font_size,
                text_color=self.text_color,
                font_weight=self.font_weight,
            )
            for character in raw_number
        ]
        self.row.controls = [
            reel.control
            for reel in self.reels
        ]

    async def initialize(self):
        """Position the mounted reels before revealing the value."""

        await asyncio.gather(
            *[
                reel.initialize()
                for reel in self.reels
            ]
        )
        await asyncio.sleep(0.04)
        self.control.opacity = 1
        self.page.update()

    async def set_value(
        self,
        new_value: int,
        transition=None,
    ):
        """Roll to a new value, retaining only the latest queued target."""

        self._pending_value = new_value
        self._pending_transition = transition

        if self._animation_running:
            return

        self._animation_running = True

        try:
            while self._pending_value is not None:
                target_value = self._pending_value
                target_transition = self._pending_transition
                self._pending_value = None
                self._pending_transition = None

                if target_value != self.value:
                    await self._animate_to(
                        target_value,
                        target_transition,
                    )
        finally:
            self._animation_running = False

    async def _animate_to(
        self,
        new_value: int,
        transition,
    ):
        old_string = str(self.value)
        new_string = str(new_value)

        if len(old_string) != len(new_string):
            self.control.opacity = 0
            self.page.update()

            self.value = new_value
            self._build(new_value)
            self.page.update()

            await asyncio.gather(
                *[
                    reel.initialize()
                    for reel in self.reels
                ]
            )
            await asyncio.sleep(0.04)

            self.control.opacity = 1
            self.page.update()

            if transition is not None:
                await transition(new_value, 0)

            return

        increasing = new_value > self.value
        changed_reels = []
        animation_tasks = []
        longest_duration = 0

        for reel, character in zip(
            self.reels,
            new_string,
            strict=True,
        ):
            target_digit = int(character)

            if target_digit != reel.value:
                changed_reels.append(reel)
                longest_duration = max(
                    longest_duration,
                    reel.animation_duration_to(
                        target_digit,
                        increasing,
                    ),
                )
                animation_tasks.append(
                    reel.roll_to(
                        target_digit,
                        increasing,
                    )
                )

        if not animation_tasks:
            self.value = new_value
            return

        reel_animation = asyncio.gather(*animation_tasks)

        if transition is None:
            await reel_animation
            await asyncio.sleep(longest_duration / 1000)
        else:
            await asyncio.gather(
                reel_animation,
                transition(
                    new_value,
                    longest_duration,
                ),
            )

        await asyncio.sleep(ANIMATION_SAFETY_MS / 1000)

        self.value = new_value

        await asyncio.gather(
            *[
                reel.recenter()
                for reel in changed_reels
            ]
        )


class RollingFormattedNumber:
    """A retained reel value with non-rolling formatting characters."""

    def __init__(
        self,
        page: ft.Page,
        display_text: str,
        *,
        digit_width: int = DIGIT_WIDTH,
        digit_height: int = DIGIT_HEIGHT,
        font_size: int = FONT_SIZE,
        text_color: str = TEXT_COLOR,
        font_weight: ft.FontWeight = ft.FontWeight.W_500,
        positive_color: str | None = None,
        negative_color: str | None = None,
    ):
        self.page = page
        self.display_text = display_text
        self.digit_width = digit_width
        self.digit_height = digit_height
        self.font_size = font_size
        self.text_color = text_color
        self.font_weight = font_weight
        self.positive_color = positive_color or text_color
        self.negative_color = negative_color or text_color

        self.reels_by_index: dict[int, DigitReel] = {}
        self.literals_by_index: dict[int, ft.Text] = {}
        self._animation_running = False
        self._pending_text: str | None = None

        self.row = ft.Row(
            spacing=0,
            tight=True,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.control = ft.Container(
            height=digit_height,
            opacity=0,
            alignment=ft.Alignment.CENTER_LEFT,
            content=self.row,
        )

        self._build(display_text)

    @staticmethod
    def _shape(display_text: str):
        return tuple(
            "digit"
            if character.isdigit()
            else "sign"
            if character in ("+", "-")
            else character
            for character in display_text
        )

    @staticmethod
    def _digits(display_text: str) -> list[int]:
        return [
            int(character)
            for character in display_text
            if character.isdigit()
        ]

    def _transition_text(
        self,
        target_text: str,
    ) -> str:
        old_digits = self._digits(self.display_text)
        target_digits = self._digits(target_text)

        if not target_digits:
            return target_text

        if len(old_digits) >= len(target_digits):
            start_digits = old_digits[-len(target_digits):]
        else:
            start_digits = (
                [0] * (len(target_digits) - len(old_digits))
                + old_digits
            )

        digit_iterator = iter(start_digits)
        return "".join(
            str(next(digit_iterator))
            if character.isdigit()
            else character
            for character in target_text
        )

    def _literal_color(self, character: str):
        if character == "+":
            return self.positive_color
        if character == "-":
            return self.negative_color
        return self.text_color

    def _build(self, display_text: str):
        self.reels_by_index = {}
        self.literals_by_index = {}
        controls = []

        for index, character in enumerate(display_text):
            if character.isdigit():
                reel = DigitReel(
                    int(character),
                    digit_width=self.digit_width,
                    digit_height=self.digit_height,
                    font_size=self.font_size,
                    text_color=self.text_color,
                    font_weight=self.font_weight,
                )
                self.reels_by_index[index] = reel
                controls.append(reel.control)
                continue

            literal = ft.Text(
                character,
                size=self.font_size,
                weight=self.font_weight,
                color=self._literal_color(character),
                no_wrap=True,
            )
            self.literals_by_index[index] = literal
            controls.append(literal)

        self.row.controls = controls

    async def initialize(self):
        """Position mounted digit reels before revealing the value."""

        await asyncio.gather(
            *[
                reel.initialize()
                for reel in self.reels_by_index.values()
            ]
        )
        await asyncio.sleep(0.04)
        self.control.opacity = 1
        self.page.update(self.control)

    async def set_text(self, display_text: str):
        """Reel to the latest queued formatted value."""

        self._pending_text = display_text

        if self._animation_running:
            return

        self._animation_running = True

        try:
            while self._pending_text is not None:
                target_text = self._pending_text
                self._pending_text = None

                if target_text != self.display_text:
                    await self._animate_to(target_text)
        finally:
            self._animation_running = False

    async def _animate_to(self, display_text: str):
        if self._shape(display_text) != self._shape(self.display_text):
            target_digits = self._digits(display_text)

            if not target_digits:
                self._build(display_text)
                self.display_text = display_text
                self.page.update(self.control)
                return

            old_digits = self._digits(self.display_text)
            old_digits_value = (
                int("".join(str(digit) for digit in old_digits))
                if old_digits
                else 0
            )
            new_digits_value = int(
                "".join(str(digit) for digit in target_digits)
            )
            increasing = (
                new_digits_value >= old_digits_value
            )

            transition_text = self._transition_text(display_text)
            self._build(transition_text)
            self.page.update(self.control)

            await asyncio.sleep(
                REEL_MOUNT_SETTLE_SECONDS
            )

            await asyncio.gather(
                *[
                    reel.initialize()
                    for reel in self.reels_by_index.values()
                ]
            )

            changed_reels = []
            animation_tasks = []
            longest_duration = 0

            for index, reel in self.reels_by_index.items():
                target_digit = int(display_text[index])

                if target_digit == reel.value:
                    continue

                changed_reels.append(reel)
                longest_duration = max(
                    longest_duration,
                    reel.animation_duration_to(
                        target_digit,
                        increasing,
                    ),
                )
                animation_tasks.append(
                    reel.roll_to(
                        target_digit,
                        increasing,
                    )
                )

            if animation_tasks:
                await asyncio.gather(*animation_tasks)
                await asyncio.sleep(longest_duration / 1000)
                await asyncio.sleep(
                    ANIMATION_SAFETY_MS / 1000
                )

            await asyncio.gather(
                *[
                    reel.recenter()
                    for reel in changed_reels
                ]
            )

            self.display_text = display_text
            return

        old_digit_string = "".join(
            character
            for character in self.display_text
            if character.isdigit()
        )
        new_digit_string = "".join(
            character
            for character in display_text
            if character.isdigit()
        )
        old_digits_value = (
            int(old_digit_string)
            if old_digit_string
            else 0
        )
        new_digits_value = (
            int(new_digit_string)
            if new_digit_string
            else 0
        )
        increasing = (
            new_digits_value >= old_digits_value
        )
        changed_reels = []
        animation_tasks = []
        longest_duration = 0

        for index, reel in self.reels_by_index.items():
            target_digit = int(display_text[index])

            if target_digit == reel.value:
                continue

            changed_reels.append(reel)
            longest_duration = max(
                longest_duration,
                reel.animation_duration_to(
                    target_digit,
                    increasing,
                ),
            )
            animation_tasks.append(
                reel.roll_to(
                    target_digit,
                    increasing,
                )
            )

        literals_changed = False

        for index, literal in self.literals_by_index.items():
            character = display_text[index]

            if literal.value != character:
                literal.value = character
                literals_changed = True

            color = self._literal_color(character)

            if literal.color != color:
                literal.color = color
                literals_changed = True

        if literals_changed:
            self.page.update(self.control)

        if animation_tasks:
            await asyncio.gather(*animation_tasks)
            await asyncio.sleep(longest_duration / 1000)
            await asyncio.sleep(ANIMATION_SAFETY_MS / 1000)

        self.display_text = display_text

        await asyncio.gather(
            *[
                reel.recenter()
                for reel in changed_reels
            ]
        )


# ============================================================
# APPLICATION
# ============================================================

async def main(page: ft.Page):

    page.title = "Rolling View Counter"

    page.bgcolor = BACKGROUND
    page.padding = 40

    page.horizontal_alignment = (
        ft.CrossAxisAlignment.CENTER
    )

    page.vertical_alignment = (
        ft.MainAxisAlignment.CENTER
    )

    # ========================================================
    # STATE
    # ========================================================

    current_views = 124_387

    animation_running = False

    reels: list[DigitReel] = []


    # ========================================================
    # COUNTER ROW
    # ========================================================

    counter_row = ft.Row(
        spacing=0,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Initially hidden while scroll positions are established.
    counter_holder = ft.Container(
        opacity=0,
        content=counter_row,
    )


    # ========================================================
    # COMMA
    # ========================================================

    def create_comma() -> ft.Container:

        return ft.Container(
            width=10,
            height=DIGIT_HEIGHT,

            alignment=ft.Alignment.CENTER,

            content=ft.Text(
                ",",
                size=FONT_SIZE,
                weight=ft.FontWeight.W_500,
                color=TEXT_COLOR,
            ),
        )


    # ========================================================
    # BUILD COUNTER
    # ========================================================

    def build_counter(value: int):

        nonlocal reels

        raw_number = str(value)

        # Create one independent reel per digit.
        reels = [
            DigitReel(int(character))
            for character in raw_number
        ]

        controls = []

        total_digits = len(raw_number)

        for index, reel in enumerate(reels):

            controls.append(
                reel.control
            )

            digits_remaining = (
                total_digits
                - index
                - 1
            )

            # Insert comma without making it scroll.
            if (
                digits_remaining > 0
                and digits_remaining % 3 == 0
            ):
                controls.append(
                    create_comma()
                )

        counter_row.controls = controls


    # Build initial value.
    build_counter(current_views)


    # ========================================================
    # SET VIEW COUNT
    # ========================================================

    async def set_views(new_views: int):

        nonlocal current_views
        nonlocal animation_running

        # Don't allow two animations to fight over the same
        # ScrollControllers.
        if animation_running:
            return

        if new_views == current_views:
            return

        animation_running = True

        try:

            old_string = str(current_views)
            new_string = str(new_views)

            # =================================================
            # NUMBER OF DIGITS CHANGED
            # =================================================
            #
            # Example:
            #
            # 999,999
            #       ↓
            # 1,000,000
            #
            # The number now physically requires another reel.
            # =================================================

            if len(old_string) != len(new_string):

                counter_holder.opacity = 0
                page.update()

                current_views = new_views

                build_counter(current_views)

                page.update()

                # Position the newly created reels.
                await asyncio.gather(
                    *[
                        reel.initialize()
                        for reel in reels
                    ]
                )

                # Give Flutter a paint opportunity.
                await asyncio.sleep(0.04)

                counter_holder.opacity = 1

                page.update()

                return


            # =================================================
            # NORMAL SAME-DIGIT-COUNT UPDATE
            # =================================================

            increasing = (
                new_views > current_views
            )

            changed_reels = []

            animation_tasks = []


            # -------------------------------------------------
            # Every digit whose visible value changes gets an
            # actual scroll animation.
            # -------------------------------------------------

            for reel, character in zip(
                reels,
                new_string,
            ):

                target_value = int(character)

                if target_value != reel.value:

                    changed_reels.append(
                        reel
                    )

                    animation_tasks.append(
                        reel.roll_to(
                            target_value,
                            increasing,
                        )
                    )


            # Defensive fallback.
            if not animation_tasks:

                current_views = new_views

                return


            # -------------------------------------------------
            # Start all independent digit reels together.
            # -------------------------------------------------

            durations = await asyncio.gather(
                *animation_tasks
            )


            # -------------------------------------------------
            # Find the reel that takes longest.
            # -------------------------------------------------

            longest_duration = max(
                durations,
                default=0,
            )


            # -------------------------------------------------
            # IMPORTANT
            #
            # Flet has dispatched the scroll animation to the
            # Flutter client.
            #
            # Do not recenter until the longest visible reel
            # has had enough time to complete.
            # -------------------------------------------------

            await asyncio.sleep(
                (
                    longest_duration
                    + ANIMATION_SAFETY_MS
                )
                / 1000
            )


            current_views = new_views


            # -------------------------------------------------
            # Silently put changed reels back into the middle
            # cycle for their next animation.
            # -------------------------------------------------

            await asyncio.gather(
                *[
                    reel.recenter()
                    for reel in changed_reels
                ]
            )


        finally:

            animation_running = False


    # ========================================================
    # DEMO BUTTONS
    # ========================================================

    async def add_one(e):

        await set_views(
            current_views + 1
        )


    async def add_ten(e):

        await set_views(
            current_views + 10
        )


    async def add_137(e):

        # Good demonstration because several reels move
        # different distances.
        await set_views(
            current_views + 137
        )


    async def add_random(e):

        amount = random.randint(
            10,
            850,
        )

        await set_views(
            current_views + amount
        )


    # ========================================================
    # YOUTUBE-STYLE VIEW CARD
    # ========================================================

    views_card = ft.Container(
        bgcolor=CARD_BACKGROUND,

        border_radius=12,

        padding=ft.Padding.symmetric(
            horizontal=20,
            vertical=15,
        ),

        content=ft.Column(
            spacing=2,
            tight=True,

            horizontal_alignment=(
                ft.CrossAxisAlignment.START
            ),

            controls=[

                counter_holder,

                ft.Text(
                    "nation",
                    size=14,
                    color=SECONDARY_TEXT,
                ),
            ],
        ),
    )


    # ========================================================
    # PAGE CONTENT
    # ========================================================

    page.add(

        ft.Column(
            spacing=28,
            tight=True,

            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),

            controls=[

                ft.Text(
                    "Seven",
                    size=20,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_COLOR,
                ),

                views_card,

                ft.Row(
                    spacing=10,

                    alignment=(
                        ft.MainAxisAlignment.CENTER
                    ),

                    controls=[

                        ft.Button(
                            "+1",
                            on_click=add_one,
                        ),

                        ft.Button(
                            "+10",
                            on_click=add_ten,
                        ),

                        ft.Button(
                            "+137",
                            on_click=add_137,
                        ),

                        ft.Button(
                            "Random",
                            on_click=add_random,
                        ),
                    ],
                ),
            ],
        )
    )


    # ========================================================
    # INITIALIZE DIGIT POSITIONS
    # ========================================================
    #
    # scroll_to() needs the Columns to already be mounted.
    # ========================================================

    await asyncio.gather(
        *[
            reel.initialize()
            for reel in reels
        ]
    )

    # Let Flutter establish the initial positions.
    await asyncio.sleep(0.04)

    counter_holder.opacity = 1

    page.update()


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    ft.run(main)
