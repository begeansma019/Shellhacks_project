import asyncio
import math

import flet as ft
import flet.canvas as cv


# ============================================================
# COLORS
# ============================================================

PAGE_BG = "#000000"

CARD_BG = ft.Colors.TRANSPARENT
CARD_BORDER = "#29292C"

PRIMARY_TEXT = "#F4F4F5"
SECONDARY_TEXT = "#929298"

DIVIDER_COLOR = "#29292C"

# ============================================================
# RISK SPECTRUM
#
# LOW RISK                                   HIGH RISK
# GREEN -> YELLOW -> GOLD -> ORANGE -> RED
# ============================================================

GREEN = "#2ECC5A"
YELLOW = "#F2D33D"
GOLD = "#F5B942"
ORANGE = "#F28C28"
ORANGE_RED = "#F26A3D"
RED = "#E53935"

GAUGE_REMAINDER = "#353538"


# ============================================================
# ANIMATION SETTINGS
# ============================================================

ANIMATION_DURATION = 0.65
ANIMATION_FPS = 30
ANIMATION_START_DELAY = 0.02

TASK_FADE_DURATION = 180
TASK_DIVIDER_DURATION = 180
TASK_SECTION_DELAY = 0.06
TASK_DIVIDER_WIDTH = 356


# ============================================================
# QUADRANT RISK CARD
# ============================================================

class QuadrantRiskCard(ft.Container):

    def __init__(
        self,
        score: int = 0,
        max_score: int = 100,
        show_title: bool = True,
    ):
        super().__init__()

        # ----------------------------------------------------
        # TARGET VALUES
        # ----------------------------------------------------

        self.target_score = max(
            0,
            min(score, max_score),
        )

        self.max_score = max_score

        self._mounted = False
        self._current_score = 0.0
        self._score_animation_generation = 0
        self._task_animation_generation = 0

        # ====================================================
        # CARD
        # ====================================================

        self.width = 400
        self.height = 436

        self.bgcolor = CARD_BG

        self.border = ft.Border.all(
            width=1,
            color=CARD_BORDER,
        )

        self.border_radius = 12

        self.padding = ft.Padding.all(22)

        self.alignment = ft.Alignment.CENTER

        # ====================================================
        # BUILD GAUGE FIRST
        # ====================================================

        gauge = self._build_gauge()

        task_specs = [
            ("Waiting for Gemini analysis", "—"),
            ("", "—"),
            ("", "—"),
            ("", "—"),
        ]
        task_controls = []
        self._task_rows = []
        self._task_items = []
        self._task_expanded = [False, False, False, False]
        self._task_animation_sequence = []

        for index, (label, value) in enumerate(task_specs):
            task_row = self._build_expandable_task(
                index,
                label,
                value,
            )
            self._task_rows.append(task_row)
            divider_line = None

            if index < len(task_specs) - 1:
                divider_line = ft.Container(
                    width=TASK_DIVIDER_WIDTH,
                    height=1,
                    bgcolor=DIVIDER_COLOR,
                )

            self._task_animation_sequence.append(
                (task_row, divider_line)
            )
            task_controls.append(task_row)

            if divider_line is not None:
                task_controls.append(
                    ft.Container(
                        height=1,
                        alignment=ft.Alignment.CENTER,
                        content=divider_line,
                    )
                )

        # ====================================================
        # CONTENT
        # ====================================================

        self.content = ft.Column(
            spacing=0,

            scroll=ft.ScrollMode.AUTO,

            alignment=ft.MainAxisAlignment.CENTER,

            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),

            controls=[

                # =================================================
                # TITLE
                # =================================================

                (
                    ft.Text(
                        "AI Risk",

                        size=18,

                        weight=ft.FontWeight.W_600,

                        color=PRIMARY_TEXT,

                        text_align=ft.TextAlign.CENTER,
                    )
                    if show_title
                    else ft.Container(height=22)
                ),

                ft.Container(height=12),

                # =================================================
                # DIVIDER
                # =================================================

                ft.Container(
                    width=350,
                    height=1,
                    bgcolor=DIVIDER_COLOR,
                ),

                ft.Container(height=14),

                # =================================================
                # GAUGE
                # =================================================

                gauge,

                ft.Container(height=12),

                # =================================================
                # LEGEND
                # =================================================

                ft.Container(
                    width=356,

                    content=ft.Column(
                        spacing=0,
                        controls=task_controls,
                    ),
                ),
            ],
        )

    # ============================================================
    # CONTROL LIFECYCLE
    # ============================================================

    def did_mount(self):
        self._mounted = True

        # Start the animation after the control has been
        # mounted into the page.
        self.page.run_task(
            self._animate_to_score
        )

    def will_unmount(self):
        self._mounted = False
        self._score_animation_generation += 1
        self._task_animation_generation += 1

    # ============================================================
    # HEX -> RGB
    # ============================================================

    @staticmethod
    def _hex_to_rgb(hex_color: str):

        hex_color = hex_color.lstrip("#")

        return tuple(
            int(
                hex_color[i:i + 2],
                16,
            )
            for i in (0, 2, 4)
        )

    # ============================================================
    # RGB -> HEX
    # ============================================================

    @staticmethod
    def _rgb_to_hex(rgb):

        values = [

            max(
                0,
                min(
                    255,
                    round(value),
                ),
            )

            for value in rgb
        ]

        return "#{:02X}{:02X}{:02X}".format(
            *values
        )

    # ============================================================
    # COLOR AT A SPECIFIC PROGRESS
    # ============================================================

    def _color_at_progress(
        self,
        progress: float,
    ):

        progress = max(
            0.0,
            min(1.0, progress),
        )

        colors = [
            GREEN,
            YELLOW,
            GOLD,
            ORANGE,
            ORANGE_RED,
            RED,
        ]

        stops = [
            0.00,
            0.20,
            0.38,
            0.58,
            0.78,
            1.00,
        ]

        for i in range(
            len(stops) - 1
        ):

            if (
                stops[i]
                <= progress
                <= stops[i + 1]
            ):

                section_progress = (
                    progress - stops[i]
                ) / (
                    stops[i + 1]
                    - stops[i]
                )

                start_rgb = (
                    self._hex_to_rgb(
                        colors[i]
                    )
                )

                end_rgb = (
                    self._hex_to_rgb(
                        colors[i + 1]
                    )
                )

                interpolated = tuple(

                    start_rgb[channel]
                    + (
                        end_rgb[channel]
                        - start_rgb[channel]
                    )
                    * section_progress

                    for channel in range(3)
                )

                return self._rgb_to_hex(
                    interpolated
                )

        return RED

    def color_for_score(self, score: float) -> str:
        maximum = float(self.max_score)
        if maximum <= 0:
            return self._color_at_progress(0.0)

        score_value = max(
            0.0,
            min(maximum, float(score)),
        )
        return self._color_at_progress(
            score_value / maximum
        )

    # ============================================================
    # EASE OUT CUBIC
    # ============================================================

    @staticmethod
    def _ease_out_cubic(t: float):

        return (
            1.0
            - pow(
                1.0 - t,
                3,
            )
        )

    # ============================================================
    # GAUGE
    # ============================================================

    def _build_gauge(self):

        # ========================================================
        # CANVAS SIZE
        # ========================================================

        self.canvas_width = 350
        self.canvas_height = 175

        # ========================================================
        # GAUGE GEOMETRY
        # ========================================================

        self.gauge_x = 22
        self.gauge_y = 14

        self.gauge_width = 306
        self.gauge_height = 270

        self.center_x = (
            self.gauge_x
            + self.gauge_width / 2
        )

        self.center_y = (
            self.gauge_y
            + self.gauge_height / 2
        )

        self.radius_x = (
            self.gauge_width / 2
        )

        self.radius_y = (
            self.gauge_height / 2
        )

        # ========================================================
        # ARC ANGLES
        # ========================================================

        self.start_angle = math.pi

        self.total_sweep = math.pi

        # ========================================================
        # INITIAL STATE
        #
        # Everything starts at score 0.
        # ========================================================

        initial_progress = 0.0

        initial_angle = (
            self.start_angle
            + (
                self.total_sweep
                * initial_progress
            )
        )

        initial_marker_x = (
            self.center_x
            + self.radius_x
            * math.cos(initial_angle)
        )

        initial_marker_y = (
            self.center_y
            + self.radius_y
            * math.sin(initial_angle)
        )

        # ========================================================
        # BACKGROUND ARC
        # ========================================================

        self._background_arc = cv.Arc(

            x=self.gauge_x,
            y=self.gauge_y,

            width=self.gauge_width,
            height=self.gauge_height,

            start_angle=self.start_angle,

            sweep_angle=self.total_sweep,

            paint=ft.Paint(

                color=GAUGE_REMAINDER,

                stroke_width=11,

                style=ft.PaintingStyle.STROKE,

                stroke_cap=ft.StrokeCap.ROUND,
            ),
        )

        # ========================================================
        # ANIMATED PROGRESS ARC
        #
        # Starts at sweep_angle = 0
        # ========================================================

        self._progress_arc = cv.Arc(

            x=self.gauge_x,
            y=self.gauge_y,

            width=self.gauge_width,
            height=self.gauge_height,

            start_angle=self.start_angle,

            sweep_angle=0,

            paint=ft.Paint(

                stroke_width=11,

                style=ft.PaintingStyle.STROKE,

                stroke_cap=ft.StrokeCap.ROUND,

                gradient=ft.PaintSweepGradient(

                    center=(
                        self.center_x,
                        self.center_y,
                    ),

                    # The gradient itself represents the
                    # complete 0 -> 100 risk spectrum.
                    start_angle=math.pi,
                    end_angle=math.pi * 2,

                    colors=[
                        GREEN,
                        YELLOW,
                        GOLD,
                        ORANGE,
                        ORANGE_RED,
                        RED,
                    ],

                    color_stops=[
                        0.00,
                        0.20,
                        0.38,
                        0.58,
                        0.78,
                        1.00,
                    ],
                ),
            ),
        )

        # ========================================================
        # ANIMATED OUTER MARKER
        # ========================================================

        self._marker_outer = cv.Circle(

            x=initial_marker_x,
            y=initial_marker_y,

            radius=12,

            paint=ft.Paint(

                color=GREEN,

                style=ft.PaintingStyle.FILL,
            ),
        )

        # ========================================================
        # ANIMATED INNER MARKER
        # ========================================================

        self._marker_inner = cv.Circle(

            x=initial_marker_x,
            y=initial_marker_y,

            radius=10,

            paint=ft.Paint(

                color= ft.Colors.BLACK,

                style=ft.PaintingStyle.FILL,
            ),
        )

        # ========================================================
        # CANVAS
        # ========================================================

        self._gauge_canvas = cv.Canvas(

            width=self.canvas_width,
            height=self.canvas_height,

            shapes=[

                self._background_arc,

                self._progress_arc,

                self._marker_outer,

                self._marker_inner,
            ],
        )

        # ========================================================
        # SCORE TEXT
        #
        # Starts at 0 and counts upward.
        # ========================================================

        self._score_text = ft.Text(

            "0",

            size=36,

            weight=ft.FontWeight.W_500,

            color=PRIMARY_TEXT,

            text_align=ft.TextAlign.CENTER,

            style=ft.TextStyle(
                height=1.0,
            ),
        )

        # ========================================================
        # GAUGE STACK
        # ========================================================

        return ft.Container(

            width=self.canvas_width,
            height=self.canvas_height,

            alignment=ft.Alignment.CENTER,

            content=ft.Stack(

                width=self.canvas_width,
                height=self.canvas_height,

                controls=[

                    # =================================================
                    # GAUGE CANVAS
                    # =================================================

                    self._gauge_canvas,

                    # =================================================
                    # RISK SCORE LABEL
                    # =================================================

                    ft.Container(
                        left=0,
                        right=0,

                        top=80,

                        alignment=ft.Alignment.CENTER,

                        content=ft.Text(

                            "Risk Score",

                            size=13,

                            color=SECONDARY_TEXT,

                            text_align=ft.TextAlign.CENTER,
                        ),
                    ),

                    # =================================================
                    # ANIMATED SCORE
                    # =================================================

                    ft.Container(
                        left=0,
                        right=0,

                        top=102,

                        alignment=ft.Alignment.CENTER,

                        content=self._score_text,
                    ),
                ],
            ),
        )

    # ============================================================
    # SET CURRENT ANIMATION FRAME
    # ============================================================

    def _set_animation_frame(
        self,
        score_value: float,
    ):

        # --------------------------------------------------------
        # Clamp animated score
        # --------------------------------------------------------

        score_value = max(
            0.0,
            min(
                float(self.max_score),
                score_value,
            ),
        )

        self._current_score = score_value

        # --------------------------------------------------------
        # Convert current score to progress
        # --------------------------------------------------------

        progress = (
            score_value
            / self.max_score
        )

        # --------------------------------------------------------
        # COLORED ARC LENGTH
        # --------------------------------------------------------

        progress_sweep = (
            self.total_sweep
            * progress
        )

        self._progress_arc.sweep_angle = (
            progress_sweep
        )

        # --------------------------------------------------------
        # MARKER POSITION
        # --------------------------------------------------------

        marker_angle = (
            self.start_angle
            + progress_sweep
        )

        marker_x = (
            self.center_x
            + self.radius_x
            * math.cos(marker_angle)
        )

        marker_y = (
            self.center_y
            + self.radius_y
            * math.sin(marker_angle)
        )

        self._marker_outer.x = marker_x
        self._marker_outer.y = marker_y

        self._marker_inner.x = marker_x
        self._marker_inner.y = marker_y

        # --------------------------------------------------------
        # MARKER COLOR
        # --------------------------------------------------------

        current_color = (
            self._color_at_progress(
                progress
            )
        )

        self._marker_outer.paint.color = (
            current_color
        )

        # --------------------------------------------------------
        # SCORE NUMBER
        # --------------------------------------------------------

        self._score_text.value = str(
            round(score_value)
        )

    # ============================================================
    # ANIMATE TO TARGET SCORE
    # ============================================================

    async def _animate_to_score(self):
        initial_target = self.target_score
        initial_generation = self._score_animation_generation

        await asyncio.sleep(
            ANIMATION_START_DELAY
        )

        if (
            not self._mounted
            or initial_generation
            != self._score_animation_generation
        ):
            return

        await self.set_score(initial_target)

    async def set_score(self, score: int):
        target_score = float(
            max(
                0,
                min(score, self.max_score),
            )
        )
        start_score = self._current_score

        self.target_score = round(target_score)
        self._score_animation_generation += 1
        generation = self._score_animation_generation

        if not self._mounted:
            self._set_animation_frame(target_score)
            return

        total_frames = max(
            1,
            round(
                ANIMATION_DURATION
                * ANIMATION_FPS
            ),
        )

        frame_delay = (
            ANIMATION_DURATION
            / total_frames
        )

        for frame in range(
            total_frames + 1
        ):
            if (
                not self._mounted
                or generation
                != self._score_animation_generation
            ):
                return

            t = (
                frame
                / total_frames
            )
            eased_t = (
                self._ease_out_cubic(t)
            )
            current_score = (
                start_score
                + (
                    target_score
                    - start_score
                )
                * eased_t
            )
            self._set_animation_frame(
                current_score
            )
            self.page.update(
                self._gauge_canvas,
                self._score_text,
            )
            if frame < total_frames:
                await asyncio.sleep(
                    frame_delay
                )

        self._set_animation_frame(
            target_score
        )
        self._score_text.value = str(
            self.target_score
        )
        self.page.update(
            self._gauge_canvas,
            self._score_text,
        )

    def set_tasks(self, tasks: list[dict]):
        for index, item in enumerate(self._task_items):
            label_control = item["label"]
            value_control = item["probability"]
            justification_control = item["justification"]

            self._task_expanded[index] = False
            item["details"].visible = False
            item["chevron"].icon = ft.Icons.CHEVRON_RIGHT

            if not tasks and index == 0:
                label_control.value = "Analyzing with Gemini…"
                value_control.value = "—"
                justification_control.value = ""
                continue

            task = tasks[index] if index < len(tasks) else None
            if isinstance(task, dict) and task.get("task"):
                label_control.value = str(task["task"])
                justification_control.value = str(
                    task.get("justification", "")
                ).strip()
                try:
                    probability = max(
                        0,
                        min(100, float(task["probability"])),
                    )
                    value_control.value = f"{round(probability)}%"
                except (KeyError, TypeError, ValueError):
                    value_control.value = "—"
            else:
                label_control.value = ""
                value_control.value = "—"
                justification_control.value = ""

        if self._mounted:
            self.page.update(*self._task_rows)

    async def animate_tasks(self):
        self._task_animation_generation += 1
        generation = self._task_animation_generation

        if not self._mounted:
            return

        for row, divider in self._task_animation_sequence:
            row.animate_opacity = None
            row.opacity = 0

            if divider is not None:
                divider.animate = None
                divider.width = 0

        self.page.update()
        await asyncio.sleep(0.02)

        if generation != self._task_animation_generation:
            return

        for row, divider in self._task_animation_sequence:
            row.animate_opacity = ft.Animation(
                duration=TASK_FADE_DURATION,
                curve=ft.AnimationCurve.EASE_IN_OUT,
            )

            if divider is not None:
                divider.animate = ft.Animation(
                    duration=TASK_DIVIDER_DURATION,
                    curve=ft.AnimationCurve.EASE_OUT,
                )

        self.page.update()
        await asyncio.sleep(0.03)

        for row, divider in self._task_animation_sequence:
            if generation != self._task_animation_generation:
                return

            row.opacity = 1

            if divider is not None:
                divider.width = TASK_DIVIDER_WIDTH

            self.page.update()
            await asyncio.sleep(TASK_SECTION_DELAY)

    # ============================================================
    # EXPANDABLE TASK
    # ============================================================

    def _build_expandable_task(
        self,
        index: int,
        label: str,
        value: str,
        justification: str = "",
    ):
        label_control = ft.Text(
            label,
            size=13,
            color=SECONDARY_TEXT,
            expand=True,
        )
        probability_control = ft.Text(
            value,
            size=13,
            color=SECONDARY_TEXT,
        )
        chevron_control = ft.Icon(
            ft.Icons.CHEVRON_RIGHT,
            size=16,
            color=SECONDARY_TEXT,
        )
        justification_control = ft.Text(
            justification,
            size=12,
            color=SECONDARY_TEXT,
        )
        details_control = ft.Container(
            visible=False,
            padding=ft.Padding.only(top=8),
            content=justification_control,
        )

        def handle_toggle(event):
            if not justification_control.value.strip():
                return

            self._task_expanded[index] = (
                not self._task_expanded[index]
            )
            details_control.visible = self._task_expanded[index]
            chevron_control.icon = (
                ft.Icons.EXPAND_MORE
                if self._task_expanded[index]
                else ft.Icons.CHEVRON_RIGHT
            )

            if self._mounted:
                self.page.update(task_container)

        header_control = ft.Container(
            on_click=handle_toggle,
            content=ft.Row(
                spacing=9,

                vertical_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),

                controls=[
                    label_control,
                    ft.Row(
                        spacing=4,
                        controls=[
                            probability_control,
                            chevron_control,
                        ],
                    ),
                ],
            ),
        )

        task_container = ft.Container(
            width=356,
            bgcolor=ft.Colors.TRANSPARENT,
            border_radius=8,
            padding=ft.Padding.symmetric(
                horizontal=12,
                vertical=9,
            ),
            content=ft.Column(
                spacing=0,
                controls=[
                    header_control,
                    details_control,
                ],
            ),
        )

        self._task_items.append(
            {
                "container": task_container,
                "header": header_control,
                "label": label_control,
                "probability": probability_control,
                "chevron": chevron_control,
                "details": details_control,
                "justification": justification_control,
            }
        )

        return task_container


# ============================================================
# MAIN
# ============================================================

def main(page: ft.Page):

    page.title = "Quadrant Risk"

    # ========================================================
    # PAGE
    # ========================================================

    page.bgcolor = PAGE_BG

    page.padding = 0

    page.horizontal_alignment = (
        ft.CrossAxisAlignment.CENTER
    )

    page.vertical_alignment = (
        ft.MainAxisAlignment.CENTER
    )

    # ========================================================
    # CARD
    # ========================================================

    page.add(

        QuadrantRiskCard(
            score=65,
            max_score=100,
        )
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    ft.run(main)
