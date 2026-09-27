import asyncio
import math
import random

import flet as ft
import flet.canvas as cv

from reel import RollingNumber


# =========================================================
# COLORS
# =========================================================

BG = "#111113"

BLACK = "#F6F6F8"
DARK = "#18181C"
TEXT = "#B9B9C3"
MUTED = "#85858F"

RED = "#F44336"
ORANGE = "#FF9800"
YELLOW = "#FFD83D"
GREEN = "#20B875"

DIVIDER = "#2A2A30"
BORDER = "#34343B"

DETAIL_FADE_DURATION = 500
DETAIL_DIVIDER_DURATION = 500
DETAIL_SECTION_DELAY = 0.35
DETAIL_DIVIDER_WIDTH = 344

SEARCH_BG = "#1B1B20"
SEARCH_COLLAPSED_WIDTH = 48
SEARCH_EXPANDED_WIDTH = 376
SEARCH_HEIGHT = 48
SEARCH_RESULT_HEIGHT = 56
SEARCH_RESULTS_PADDING = 12
SEARCH_MAX_RESULTS = 6

CHIP_BG = "#202026"
CHIP_BORDER = "#34343C"

CHIP_SELECTED_BG = "#F0F0F3"
CHIP_SELECTED_TEXT = "#151518"


# =========================================================
# OCCUPATIONS
# =========================================================

OCCUPATIONS = [
    "Software Engineer",
    "Teacher",
    "Graphic Designer",
    "Accountant",
    "Nurse",
    "Electrician",
    "Architect",
    "Data Analyst",
    "Photographer",
    "Lawyer",
    "Marketing Manager",
    "Web Developer",
    "Mechanical Engineer",
    "Chef",
    "Financial Analyst",
    "Art Director",
    "Product Manager",
    "UX Designer",
    "Journalist",
    "Real Estate Agent",
]

OCCUPATION_CATEGORIES = {
    "Software Engineer": "Computer and Information Technology",
    "Teacher": "Education",
    "Graphic Designer": "Arts and Design",
    "Accountant": "Business and Finance",
    "Nurse": "Healthcare",
    "Electrician": "Construction and Trades",
    "Architect": "Architecture and Engineering",
    "Data Analyst": "Mathematics and Data",
    "Photographer": "Arts and Design",
    "Lawyer": "Legal",
    "Marketing Manager": "Management",
    "Web Developer": "Computer and Information Technology",
    "Mechanical Engineer": "Engineering",
    "Chef": "Food and Hospitality",
    "Financial Analyst": "Business and Finance",
    "Art Director": "Arts and Design",
    "Product Manager": "Management",
    "UX Designer": "Arts and Design",
    "Journalist": "Media and Communication",
    "Real Estate Agent": "Sales",
}

RISK_SCORE_MAX = 600


def occupation_risk_score(name: str) -> int:
    weighted_name = sum(
        position * ord(character)
        for position, character in enumerate(
            name,
            start=1,
        )
    )
    return 100 + weighted_name % 501


# =========================================================
# EXPANDABLE SEARCH
# =========================================================

def expandable_search(
    page: ft.Page,
    select_occupation,
):
    search_expanded = False
    results_open = False

    selected_result_text = ft.Text(
        value="",
        size=12,
        color=MUTED,
        visible=False,
    )

    results_column = ft.Column(
        controls=[],
        spacing=0,
        tight=True,
    )

    results_container = ft.Container(
        width=SEARCH_EXPANDED_WIDTH,
        height=0,
        opacity=0,
        bgcolor="#202124",
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate=ft.Animation(
            duration=220,
            curve=ft.AnimationCurve.EASE_OUT,
        ),
        animate_opacity=ft.Animation(
            duration=260,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        ),
        content=results_column,
    )

    def filter_results(query: str):
        normalized_query = query.strip().lower()

        if not normalized_query:
            return []

        matches = []

        for title in OCCUPATIONS:
            category = OCCUPATION_CATEGORIES[title]
            searchable_text = f"{title} {category}".lower()

            if normalized_query in searchable_text:
                matches.append(
                    {
                        "title": title,
                        "category": category,
                    }
                )

        matches.sort(
            key=lambda occupation: (
                not occupation["title"]
                .lower()
                .startswith(normalized_query),
                occupation["title"],
            )
        )

        return matches[:SEARCH_MAX_RESULTS]

    def hide_results():
        nonlocal results_open

        results_open = False
        results_container.opacity = 0
        results_container.height = 0

    def calculate_results_height(result_count: int):
        if result_count <= 0:
            return (
                SEARCH_RESULT_HEIGHT
                + SEARCH_RESULTS_PADDING
            )

        divider_count = max(0, result_count - 1)
        return (
            result_count * SEARCH_RESULT_HEIGHT
            + divider_count
            + SEARCH_RESULTS_PADDING
        )

    def create_result_click_handler(occupation):
        async def select_result(e):
            search_field.value = occupation["title"]
            clear_button.visible = True

            hide_results()

            selected_result_text.value = (
                f"Selected: {occupation['title']}"
            )
            selected_result_text.visible = True

            page.update()
            await search_field.focus()
            await select_occupation(occupation["title"])

        return select_result

    def create_result_control(occupation):
        return ft.Container(
            height=SEARCH_RESULT_HEIGHT,
            padding=ft.Padding.symmetric(
                horizontal=16,
                vertical=8,
            ),
            border_radius=12,
            ink=True,
            ink_color=ft.Colors.WHITE_10,
            on_click=create_result_click_handler(occupation),
            content=ft.Row(
                controls=[
                    ft.Icon(
                        icon=ft.Icons.SEARCH_ROUNDED,
                        size=20,
                        color=TEXT,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                value=occupation["title"],
                                size=14,
                                color=BLACK,
                                weight=ft.FontWeight.W_500,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                value=occupation["category"],
                                size=11,
                                color=MUTED,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=2,
                        tight=True,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def show_results(matches, query: str):
        nonlocal results_open

        results_column.controls.clear()

        if matches:
            for index, occupation in enumerate(matches):
                results_column.controls.append(
                    create_result_control(occupation)
                )

                if index < len(matches) - 1:
                    results_column.controls.append(
                        ft.Divider(
                            height=1,
                            thickness=1,
                            color=ft.Colors.WHITE_10,
                        )
                    )

            result_count = len(matches)
        else:
            results_column.controls.append(
                ft.Container(
                    height=SEARCH_RESULT_HEIGHT,
                    padding=ft.Padding.symmetric(horizontal=16),
                    alignment=ft.Alignment.CENTER_LEFT,
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                icon=ft.Icons.SEARCH_OFF_ROUNDED,
                                size=20,
                                color=MUTED,
                            ),
                            ft.Text(
                                value=(
                                    f'No results found for "{query}"'
                                ),
                                size=13,
                                color=MUTED,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=12,
                    ),
                )
            )
            result_count = 0

        results_container.height = calculate_results_height(
            result_count
        )
        results_container.opacity = 1
        results_open = True

    async def expand_search():
        nonlocal search_expanded

        search_expanded = True
        search_field.visible = True
        search_container.width = SEARCH_EXPANDED_WIDTH
        search_button.tooltip = "Search"

        page.update()
        await search_field.focus()

    def collapse_search():
        nonlocal search_expanded

        search_expanded = False
        search_field.value = ""
        search_field.visible = False
        clear_button.visible = False
        search_container.width = SEARCH_COLLAPSED_WIDTH
        search_button.tooltip = "Open search"

        hide_results()
        selected_result_text.value = ""
        selected_result_text.visible = False

        page.update()

    async def search_button_clicked(e):
        if not search_expanded:
            await expand_search()
            return

        query = search_field.value.strip()

        if not query:
            collapse_search()
            return

        show_results(filter_results(query), query)
        page.update()

    def search_text_changed(e):
        query = search_field.value.strip()
        clear_button.visible = bool(query)
        selected_result_text.value = ""
        selected_result_text.visible = False

        if query:
            show_results(filter_results(query), query)
        else:
            hide_results()

        page.update()

    async def clear_search(e):
        search_field.value = ""
        clear_button.visible = False
        selected_result_text.value = ""
        selected_result_text.visible = False

        hide_results()

        page.update()
        await search_field.focus()

    async def submit_search(e):
        query = search_field.value.strip()

        if query:
            show_results(filter_results(query), query)
        else:
            hide_results()
            selected_result_text.value = ""
            selected_result_text.visible = False

        page.update()

    search_button = ft.IconButton(
        icon=ft.Icons.SEARCH_ROUNDED,
        icon_color=BLACK,
        icon_size=24,
        width=SEARCH_HEIGHT,
        height=SEARCH_HEIGHT,
        padding=0,
        alignment=ft.Alignment.CENTER,
        tooltip="Open search",
        hover_color=ft.Colors.WHITE_10,
        on_click=search_button_clicked,
    )

    search_field = ft.TextField(
        expand=True,
        visible=False,
        hint_text="Search occupations...",
        border=ft.InputBorder.NONE,
        text_size=14,
        color=BLACK,
        cursor_color=BLACK,
        hint_style=ft.TextStyle(
            size=14,
            color=MUTED,
        ),
        content_padding=ft.Padding.only(
            left=2,
            right=4,
            top=0,
            bottom=0,
        ),
        on_change=search_text_changed,
        on_submit=submit_search,
    )

    clear_button = ft.IconButton(
        icon=ft.Icons.CLOSE_ROUNDED,
        icon_color=TEXT,
        icon_size=20,
        width=44,
        height=SEARCH_HEIGHT,
        padding=0,
        alignment=ft.Alignment.CENTER,
        tooltip="Clear search",
        visible=False,
        hover_color=ft.Colors.WHITE_10,
        on_click=clear_search,
    )

    search_container = ft.Container(
        width=SEARCH_COLLAPSED_WIDTH,
        height=SEARCH_HEIGHT,
        bgcolor=SEARCH_BG,
        border_radius=SEARCH_HEIGHT / 2,
        padding=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate=ft.Animation(
            duration=300,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        ),
        content=ft.Row(
            controls=[
                search_button,
                search_field,
                clear_button,
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    return ft.Container(
        top=8,
        right=12,
        width=SEARCH_EXPANDED_WIDTH,
        content=ft.Column(
            controls=[
                search_container,
                results_container,
                selected_result_text,
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        ),
    )


# =========================================================
# OCCUPATION LIST
# =========================================================

def occupation_list(
    page: ft.Page,
    title_text: ft.Text,
    score_reel: RollingNumber,
    animate_ring,
    animate_details,
    on_occupation_selected,
):
    selected_occupations = random.sample(
        OCCUPATIONS,
        k=10,
    )

    chips = []

    async def select_occupation(
        name: str,
        selected_chip: ft.Container | None = None,
    ):
        # Reset chips
        for chip in chips:
            chip.bgcolor = CHIP_BG
            chip.border = ft.Border.all(
                1,
                CHIP_BORDER,
            )
            chip.content.color = TEXT
            chip.content.weight = ft.FontWeight.W_500

        # Highlight selected chip
        if selected_chip is not None:
            selected_chip.bgcolor = CHIP_SELECTED_BG
            selected_chip.border = ft.Border.all(
                1,
                CHIP_SELECTED_BG,
            )
            selected_chip.content.color = CHIP_SELECTED_TEXT
            selected_chip.content.weight = ft.FontWeight.W_600

        title_text.value = f"Risk Score • {name}"

        new_score = occupation_risk_score(name)

        on_occupation_selected(
            name,
            new_score,
        )

        page.update()

        await asyncio.gather(
            score_reel.set_value(
                new_score,
                animate_ring,
            ),
            animate_details(),
        )

    # Build occupation chips
    for occupation in selected_occupations:
        chip = ft.Container(
            height=38,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(
                horizontal=9,
                vertical=2,
            ),
            bgcolor=CHIP_BG,
            border_radius=11,
            border=ft.Border.all(
                1,
                CHIP_BORDER,
            ),
            content=ft.Text(
                occupation,
                size=12,
                color=TEXT,
                weight=ft.FontWeight.W_500,
                no_wrap=True,
            ),
        )

        async def handle_occupation_click(
            e,
            name=occupation,
            control=chip,
        ):
            await select_occupation(
                name,
                control,
            )

        chip.on_click = handle_occupation_click

        chips.append(chip)

    occupation_view = ft.ListView(
        horizontal=True,
        height=44,
        spacing=8,

        scroll=ft.Scrollbar(
            thickness=0,
            interactive=False,
            thumb_visibility=False,
            track_visibility=False,
        ),

        controls=chips,
    )

    return (
        ft.Container(
            height=52,
            padding=ft.Padding.only(
                left=16,
                right=16,
                bottom=8,
            ),
            content=occupation_view,
        ),
        select_occupation,
    )


# =========================================================
# PAGE HEADER
# =========================================================

def header(title_text: ft.Text):
    return ft.Container(
        height=44,
        alignment=ft.Alignment.CENTER,
        content=title_text,
    )


# =========================================================
# RISK SCORE GAUGE
# =========================================================

def risk_score_gauge(
    page: ft.Page,
    score_reel: RollingNumber,
    score: int = 331,
):

    gauge_width = 360
    gauge_height = 205

    arc_x = 10
    arc_y = 18

    arc_width = 340
    arc_height = 304

    center_x = arc_x + arc_width / 2
    center_y = arc_y + arc_height / 2

    track_arc = cv.Arc(
        x=arc_x,
        y=arc_y,
        width=arc_width,
        height=arc_height,
        start_angle=math.pi,
        sweep_angle=math.pi,
        paint=ft.Paint(
            color="#3D3D42",
            stroke_width=12,
            style=ft.PaintingStyle.STROKE,
            stroke_cap=ft.StrokeCap.ROUND,
        ),
    )

    progress_arc = cv.Arc(
        x=arc_x,
        y=arc_y,
        width=arc_width,
        height=arc_height,
        start_angle=math.pi,
        sweep_angle=0,
        paint=ft.Paint(
            stroke_width=12,
            style=ft.PaintingStyle.STROKE,
            stroke_cap=ft.StrokeCap.ROUND,
            gradient=ft.PaintSweepGradient(
                center=(
                    center_x,
                    center_y,
                ),
                start_angle=math.pi,
                end_angle=math.pi * 2,
                colors=[
                    "#2ECC5A",
                    "#F2D33D",
                    "#F28C28",
                    "#E53935",
                ],
                color_stops=[
                    0.00,
                    0.33,
                    0.66,
                    1.00,
                ],
            ),
        ),
    )

    thumb_fill = cv.Circle(
        x=0,
        y=0,
        radius=12,
        paint=ft.Paint(
            color=BG,
            style=ft.PaintingStyle.FILL,
        ),
    )

    thumb_outline = cv.Circle(
        x=0,
        y=0,
        radius=13,
        paint=ft.Paint(
            color=ORANGE,
            stroke_width=3,
            style=ft.PaintingStyle.STROKE,
        ),
    )

    def set_score(new_score: float):
        progress = max(
            0.0,
            min(new_score / RISK_SCORE_MAX, 1.0),
        )
        angle = math.pi + math.pi * progress

        progress_arc.sweep_angle = math.pi * progress

        thumb_x = (
            center_x
            + arc_width / 2 * math.cos(angle)
        )
        thumb_y = (
            center_y
            + arc_height / 2 * math.sin(angle)
        )

        thumb_fill.x = thumb_x
        thumb_fill.y = thumb_y
        thumb_outline.x = thumb_x
        thumb_outline.y = thumb_y

    async def animate_score(
        new_score: int,
        duration_ms: int,
    ):
        if duration_ms <= 0:
            set_score(new_score)
            page.update()
            return

        start_score = (
            progress_arc.sweep_angle
            / math.pi
            * RISK_SCORE_MAX
        )
        score_delta = new_score - start_score
        duration_seconds = duration_ms / 1000
        loop = asyncio.get_running_loop()
        start_time = loop.time()

        while True:
            elapsed = loop.time() - start_time
            progress = min(
                elapsed / duration_seconds,
                1.0,
            )
            eased_progress = (
                1 - math.cos(math.pi * progress)
            ) / 2

            set_score(
                start_score
                + score_delta * eased_progress
            )
            page.update()

            if progress >= 1.0:
                break

            await asyncio.sleep(
                min(
                    1 / 60,
                    duration_seconds - elapsed,
                )
            )

    set_score(score)

    gauge_canvas = cv.Canvas(
        width=gauge_width,
        height=gauge_height,
        shapes=[
            track_arc,
            progress_arc,
            thumb_fill,
            thumb_outline,
        ],
    )

    # -----------------------------------------------------
    # Risk Score text
    #
    # This is intentionally a completely separate overlay
    # from the canvas.
    # -----------------------------------------------------

    score_overlay = ft.Container(
        left=0,
        top=70,

        width=gauge_width,
        height=100,

        alignment=ft.Alignment.CENTER,

        content=ft.Column(
            spacing=3,

            alignment=ft.MainAxisAlignment.CENTER,

            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),

            controls=[
                ft.Text(
                    "Risk Score",
                    size=15,
                    color=MUTED,
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                ),

                score_reel.control,
            ],
        ),
    )

    gauge = ft.Container(
        height=gauge_height,

        alignment=ft.Alignment.TOP_CENTER,

        content=ft.Stack(
            width=gauge_width,
            height=gauge_height,

            controls=[
                # Canvas rendered first
                gauge_canvas,

                # Score rendered last and therefore on top
                score_overlay,
            ],
        ),
    )

    return gauge, animate_score


# =========================================================
# BOTTOM SHEET
# =========================================================

def show_detail_sheet(
    page: ft.Page,
    title: str,
    status: str | None,
    value: str,
    description: str,
    status_color: str = GREEN,
):

    sheet_controls = [
        ft.Text(
            title,
            size=21,
            weight=ft.FontWeight.W_700,
            color=BLACK,
        ),

        ft.Text(
            value,
            size=34,
            weight=ft.FontWeight.W_700,
            color=BLACK,
        ),
    ]

    if status is not None:
        sheet_controls.append(
            ft.Container(
                padding=ft.Padding.symmetric(
                    horizontal=9,
                    vertical=2,
                ),
                bgcolor=CHIP_BG,
                border_radius=15,
                content=ft.Text(
                    status,
                    size=12,
                    color=status_color,
                    weight=ft.FontWeight.W_600,
                ),
            )
        )

    sheet_controls.extend(
        [
            ft.Container(height=8),

            ft.Text(
                description,
                size=14,
                color=TEXT,
            ),

            ft.Container(height=12),

            ft.Button(
                content="Close",
                on_click=lambda e: page.pop_dialog(),
            ),
        ]
    )

    sheet = ft.BottomSheet(
        bgcolor="#1B1B1B",
        dismissible=True,
        draggable=True,
        show_drag_handle=True,

        content=ft.Container(
            padding=ft.Padding.only(
                left=24,
                right=24,
                top=8,
                bottom=28,
            ),

            content=ft.Column(
                tight=True,
                spacing=8,
                controls=sheet_controls,
            ),
        ),
    )

    page.show_dialog(sheet)


# =========================================================
# CLICKABLE DETAIL ROW
# =========================================================

def detail_row(
    page: ft.Page,
    title: str,
    status: str | None,
    value: str,
    description: str,
    status_color: str = GREEN,
    show_divider: bool = True,
):

    def row_clicked(e):
        show_detail_sheet(
            page=page,
            title=title,
            status=status,
            value=value,
            description=description,
            status_color=status_color,
        )

    row = ft.Container(
        height=63,

        opacity=0,
        animate_opacity=ft.Animation(
            duration=DETAIL_FADE_DURATION,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        ),

        padding=ft.Padding.symmetric(
            horizontal=16,
            vertical=9,
        ),

        on_click=row_clicked,

        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,

            controls=[
                # Left
                ft.Column(
                    spacing=3,
                    alignment=ft.MainAxisAlignment.CENTER,

                    controls=[
                        ft.Text(
                            title,
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                        ),

                        *(
                            [
                                ft.Text(
                                    status,
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                    color=status_color,
                                )
                            ]
                            if status is not None
                            else []
                        ),
                    ],
                ),

                # Right
                ft.Row(
                    spacing=7,

                    controls=[
                        ft.Text(
                            value,
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=BLACK,
                        ),

                        ft.Icon(
                            ft.Icons.CHEVRON_RIGHT,
                            size=18,
                            color=MUTED,
                        ),
                    ],
                ),
            ],
        ),
    )

    controls = [row]
    divider_line = None

    if show_divider:
        divider_line = ft.Container(
            width=0,
            height=1,
            bgcolor=DIVIDER,
            animate=ft.Animation(
                duration=DETAIL_DIVIDER_DURATION,
                curve=ft.AnimationCurve.EASE_OUT,
            ),
        )

        controls.append(
            ft.Container(
                height=1,
                margin=ft.Margin.symmetric(
                    horizontal=16,
                ),
                alignment=ft.Alignment.CENTER,
                content=divider_line,
            )
        )

    return (
        ft.Column(
            spacing=0,
            controls=controls,
        ),
        row,
        divider_line,
    )


# =========================================================
# RISK DETAILS CARD
# =========================================================

def risk_details_card(page: ft.Page):

    task_analysis = detail_row(
        page=page,
        title="Analyze Information",
        status="High Risk",
        value="82%",
        status_color=RED,
        description=(
            "The estimated share of information-analysis work "
            "exposed to automation for this occupation."
        ),
    )

    task_data = detail_row(
        page=page,
        title="Process Routine Data",
        status="High Risk",
        value="74%",
        status_color=RED,
        description=(
            "The estimated share of routine data-processing work "
            "exposed to automation for this occupation."
        ),
    )

    task_communication = detail_row(
        page=page,
        title="Communicate with Others",
        status="Moderate Risk",
        value="48%",
        status_color=ORANGE,
        description=(
            "The estimated share of communication work exposed "
            "to automation for this occupation."
        ),
    )

    task_problem_solving = detail_row(
        page=page,
        title="Solve Complex Problems",
        status="Low Risk",
        value="31%",
        description=(
            "The estimated share of complex problem-solving work "
            "exposed to automation for this occupation."
        ),
    )

    task_decisions = detail_row(
        page=page,
        title="Make Decisions",
        status="Low Risk",
        value="18%",
        description=(
            "The estimated share of decision-making work exposed "
            "to automation for this occupation."
        ),
        show_divider=False,
    )

    detail_rows = [
        task_analysis,
        task_data,
        task_communication,
        task_problem_solving,
        task_decisions,
    ]

    card = ft.Container(
        bgcolor="#000000",

        border_radius=18,

        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,

        content=ft.Column(
            spacing=0,

            controls=[
                ft.Container(
                    padding=ft.Padding.only(
                        left=16,
                        right=16,
                        top=8,
                        bottom=4,
                    ),
                    content=ft.Text(
                        "Main Tasks",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color=BLACK,
                    ),
                ),
                *[
                    detail_control
                    for detail_control, _, _ in detail_rows
                ],
            ],
        ),
    )

    animation_sequence = [
        (row, divider)
        for _, row, divider in detail_rows
    ]

    return card, animation_sequence


class RiskDetailsAnimator:

    def __init__(
        self,
        page: ft.Page,
        animation_sequence,
    ):
        self.page = page
        self.animation_sequence = animation_sequence
        self.generation = 0

    async def play(self):
        self.generation += 1
        generation = self.generation

        # Reset without playing the animations in reverse.
        for row, divider in self.animation_sequence:
            row.animate_opacity = None
            row.opacity = 0

            if divider is not None:
                divider.animate = None
                divider.width = 0

        self.page.update()
        await asyncio.sleep(0.04)

        if generation != self.generation:
            return

        for row, divider in self.animation_sequence:
            row.animate_opacity = ft.Animation(
                duration=DETAIL_FADE_DURATION,
                curve=ft.AnimationCurve.EASE_IN_OUT,
            )

            if divider is not None:
                divider.animate = ft.Animation(
                    duration=DETAIL_DIVIDER_DURATION,
                    curve=ft.AnimationCurve.EASE_OUT,
                )

        self.page.update()
        await asyncio.sleep(0.1)

        for row, divider in self.animation_sequence:
            if generation != self.generation:
                return

            row.opacity = 1

            if divider is not None:
                divider.width = DETAIL_DIVIDER_WIDTH

            self.page.update()
            await asyncio.sleep(DETAIL_SECTION_DELAY)


# =========================================================
# BOTTOM NAVIGATION
# =========================================================

def occupation_overview_page():
    occupation_name = ft.Text(
        "Select an occupation",
        size=21,
        weight=ft.FontWeight.W_700,
        color=BLACK,
    )
    category_text = ft.Text(
        "Choose an occupation above to see its overview.",
        size=13,
        color=TEXT,
    )
    risk_summary = ft.Text(
        "The overview will update with the selected risk score.",
        size=14,
        color=TEXT,
    )

    def update_occupation(
        name: str,
        risk_score: int,
    ):
        occupation_name.value = name
        category_text.value = OCCUPATION_CATEGORIES[name]

        if risk_score >= 400:
            risk_label = "High automation exposure"
            risk_color = RED
        elif risk_score >= 250:
            risk_label = "Moderate automation exposure"
            risk_color = ORANGE
        else:
            risk_label = "Low automation exposure"
            risk_color = GREEN

        risk_summary.value = (
            f"{risk_label} • {risk_score} of {RISK_SCORE_MAX}"
        )
        risk_summary.color = risk_color

    return (
        ft.Container(
            expand=True,
            padding=ft.Padding.only(
                left=12,
                right=12,
                top=4,
                bottom=8,
            ),
            content=ft.Container(
                bgcolor="#000000",
                border_radius=18,
                padding=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Overview",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=BLACK,
                        ),
                        occupation_name,
                        category_text,
                        ft.Container(height=6),
                        risk_summary,
                    ],
                ),
            ),
        ),
        update_occupation,
    )


def market_information_page():
    occupation_name = ft.Text(
        "Select an occupation",
        size=21,
        weight=ft.FontWeight.W_700,
        color=BLACK,
    )
    category_text = ft.Text(
        "Choose an occupation above to view market information.",
        size=13,
        color=TEXT,
    )
    salary_value = ft.Text(
        "—",
        size=18,
        weight=ft.FontWeight.W_700,
        color=BLACK,
    )
    growth_value = ft.Text(
        "—",
        size=18,
        weight=ft.FontWeight.W_700,
        color=BLACK,
    )
    openings_value = ft.Text(
        "—",
        size=18,
        weight=ft.FontWeight.W_700,
        color=BLACK,
    )

    def market_metric(
        label: str,
        value_control: ft.Text,
    ):
        return ft.Container(
            expand=True,
            bgcolor=DARK,
            border_radius=12,
            padding=12,
            content=ft.Column(
                spacing=5,
                controls=[
                    ft.Text(
                        label,
                        size=11,
                        color=MUTED,
                    ),
                    value_control,
                ],
            ),
        )

    def update_occupation(
        name: str,
        risk_score: int,
    ):
        market_seed = sum(
            position * ord(character)
            for position, character in enumerate(
                name,
                start=1,
            )
        )
        estimated_salary = 52000 + market_seed % 89001
        projected_growth = 3 + market_seed % 16
        annual_openings = 5000 + market_seed % 95001

        occupation_name.value = name
        category_text.value = OCCUPATION_CATEGORIES[name]
        salary_value.value = f"${estimated_salary:,}"
        growth_value.value = f"+{projected_growth}%"
        openings_value.value = f"{annual_openings:,}"

    return (
        ft.Container(
            expand=True,
            padding=ft.Padding.only(
                left=12,
                right=12,
                top=4,
                bottom=8,
            ),
            content=ft.Container(
                bgcolor="#000000",
                border_radius=18,
                padding=18,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Text(
                            "Market Information",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=BLACK,
                        ),
                        occupation_name,
                        category_text,
                        ft.Row(
                            spacing=8,
                            controls=[
                                market_metric(
                                    "Estimated pay",
                                    salary_value,
                                ),
                                market_metric(
                                    "Growth",
                                    growth_value,
                                ),
                            ],
                        ),
                        market_metric(
                            "Estimated annual openings",
                            openings_value,
                        ),
                        ft.Text(
                            "Illustrative estimates for the selected occupation.",
                            size=10,
                            color=MUTED,
                        ),
                    ],
                ),
            ),
        ),
        update_occupation,
    )

def nav_item(
    icon,
    label: str,
    index: int,
    on_click,
    selected: bool = False,
):

    color = RED if selected else MUTED

    icon_control = ft.Icon(
        icon,
        size=22,
        color=color,
    )
    label_control = ft.Text(
        label,
        size=10,
        color=color,
        weight=(
            ft.FontWeight.W_600
            if selected
            else ft.FontWeight.W_400
        ),
    )

    item = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        data=index,
        on_click=on_click,

        content=ft.Column(
            spacing=3,

            alignment=ft.MainAxisAlignment.CENTER,

            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),

            controls=[
                icon_control,
                label_control,
            ],
        ),
    )

    return item, icon_control, label_control


def bottom_navigation(
    page: ft.Page,
    page_view: ft.PageView,
    selected_index: int,
):
    destinations = [
        (
            ft.Icons.DASHBOARD_OUTLINED,
            "Overview",
        ),
        (
            ft.Icons.CHECKLIST_ROUNDED,
            "Tasks",
        ),
        (
            ft.Icons.QUERY_STATS_ROUNDED,
            "Market",
        ),
    ]
    navigation_items = []

    def show_selected_item(index: int):
        for item_index, (_, icon, label) in enumerate(
            navigation_items
        ):
            selected = item_index == index
            color = RED if selected else MUTED
            icon.color = color
            label.color = color
            label.weight = (
                ft.FontWeight.W_600
                if selected
                else ft.FontWeight.W_400
            )

    async def navigate(event):
        target_index = int(event.control.data)
        show_selected_item(target_index)
        page.update(navigation)

        if target_index == page_view.selected_index:
            return

        await page_view.go_to_page(
            target_index,
            animation_duration=450,
            animation_curve=ft.AnimationCurve.EASE_IN_OUT,
        )

    for index, (icon, label) in enumerate(destinations):
        navigation_items.append(
            nav_item(
                icon,
                label,
                index,
                navigate,
                selected=index == selected_index,
            )
        )

    navigation = ft.Container(
        height=65,
        bgcolor=BG,

        border=ft.Border(
            top=ft.BorderSide(
                width=1,
                color=DIVIDER,
            ),
        ),

        content=ft.Row(
            spacing=0,
            controls=[
                item
                for item, _, _ in navigation_items
            ],
        ),
    )

    def page_changed(event):
        show_selected_item(event.control.selected_index)
        page.update(navigation)

    page_view.on_change = page_changed

    return navigation


# =========================================================
# MAIN
# =========================================================

async def main(page: ft.Page):

    # -----------------------------------------------------
    # Window
    # -----------------------------------------------------

    page.title = "Risk Score"

    page.window.width = 400
    page.window.height = 800

    # -----------------------------------------------------
    # Page styling
    # -----------------------------------------------------

    page.padding = 0
    page.spacing = 0

    page.bgcolor = ft.Colors.BLACK

    page.theme_mode = ft.ThemeMode.DARK

    # -----------------------------------------------------
    # Main title
    # -----------------------------------------------------

    title_text = ft.Text(
        "Risk Score",
        size=17,
        weight=ft.FontWeight.W_600,
        color=BLACK,
        text_align=ft.TextAlign.CENTER,
    )

    score_reel = RollingNumber(
        page,
        331,
        digit_width=34,
        digit_height=60,
        font_size=50,
        text_color=BLACK,
        font_weight=ft.FontWeight.W_700,
    )

    gauge_control, animate_ring = risk_score_gauge(
        page,
        score_reel
    )

    details_card, details_animation = risk_details_card(
        page
    )
    details_animator = RiskDetailsAnimator(
        page,
        details_animation,
    )

    overview_page, update_overview = (
        occupation_overview_page()
    )
    market_page, update_market = (
        market_information_page()
    )

    def update_occupation_pages(
        name: str,
        risk_score: int,
    ):
        update_overview(
            name,
            risk_score,
        )
        update_market(
            name,
            risk_score,
        )

    occupation_control, select_occupation = occupation_list(
        page,
        title_text,
        score_reel,
        animate_ring,
        details_animator.play,
        update_occupation_pages,
    )
    search_control = expandable_search(
        page,
        select_occupation,
    )

    # -----------------------------------------------------
    # Layout
    # -----------------------------------------------------

    tasks_page = ft.Container(
        expand=True,
        padding=ft.Padding.only(
            left=12,
            right=12,
            top=4,
            bottom=8,
        ),
        content=details_card,
    )
    content_page_view = ft.PageView(
        expand=True,
        controls=[
            overview_page,
            tasks_page,
            market_page,
        ],
        selected_index=1,
        keep_page=True,
        horizontal=True,
        viewport_fraction=1.0,
        pad_ends=False,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    bottom_app_bar = bottom_navigation(
        page,
        content_page_view,
        selected_index=1,
    )

    page.add(
        ft.Stack(
            expand=True,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        # Space reserved for the top-right search.
                        ft.Container(height=64),

                        # Occupations
                        occupation_control,

                        # Page title
                        header(
                            title_text,
                        ),

                        # Risk score
                        gauge_control,

                        # Occupation content pages
                        content_page_view,

                        # Bottom navigation
                        bottom_app_bar,
                    ],
                ),

                # Search is rendered last so its results overlay
                # the dashboard instead of moving the layout.
                search_control,
            ],
        ),
    )

    await score_reel.initialize()
    await details_animator.play()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    ft.run(main)
