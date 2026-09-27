import asyncio
import os
from importlib import import_module
from pathlib import Path

import flet as ft

import search as occupation_search
from gemini_risk_service import (
    GeminiRiskService,
    GeminiRiskServiceError,
)
from occupation_service import OccupationService
from oews_service import OewsDataError, OewsWageService
from onet_service import OnetService, OnetServiceError
from reel import RollingFormattedNumber


PAGE_BG = "#000000"
APPBAR_BG = "#050505"
PRIMARY_TEXT = "#F4F4F5"
SECONDARY_TEXT = "#B9B9C3"
CHIP_BG = "#070707"
CHIP_BORDER = "#292929"
CHIP_TEXT = "#888888"
CHIP_SELECTED_BG = "#FFFFFF"
CHIP_SELECTED_TEXT = "#000000"
CARD_GAP = 24
RIGHT_CARD_GAP = 8
RIGHT_COLUMN_WIDTH = 400
PAGE_PADDING = 5
SKILLS_CARD_HEIGHT = 320
METRIC_CARD_HEIGHT = 140
METRIC_GREEN = "#18D66B"
METRIC_RED = "#FF4D4D"


# Scenario assumptions for the replacement-economics model.
# Gemini 3.8 Flash paid-tier token rates shown here are the
# introductory rates through 2026-12-31. Other cost inputs are
# explicit planning assumptions, not measured production costs.
WORK_HOURS_PER_YEAR = 2080

GEMINI_INPUT_PRICE_PER_MILLION = 0.75
GEMINI_OUTPUT_PRICE_PER_MILLION = 3.75

ASSUMED_INPUT_TOKENS_PER_AUTOMATED_HOUR = 20_000
ASSUMED_OUTPUT_TOKENS_PER_AUTOMATED_HOUR = 5_000

ASSUMED_SOFTWARE_INFRA_ANNUAL = 3_000
ASSUMED_HUMAN_OVERSIGHT_SHARE = 0.10

ASSUMED_IMPLEMENTATION_COST = 20_000
ASSUMED_IMPLEMENTATION_USEFUL_LIFE_YEARS = 3
ASSUMED_MAINTENANCE_RATE = 0.10

SEARCH_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-search preview-icon"><path d="m21 21-4.34-4.34"/><circle cx="11" cy="11" r="8"/></svg>"""
CLOSE_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-x preview-icon"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>"""
LOCAL_ENV_PATH = Path(__file__).with_name(".env")
DEFAULT_OCCUPATIONS = (
    {"code": "15-1252.00", "title": "Software Developers"},
    {"code": "47-2111.00", "title": "Electricians"},
    {"code": "29-1051.00", "title": "Pharmacists"},
    {"code": "41-2011.00", "title": "Cashiers"},
    {"code": "47-2031.00", "title": "Carpenters"},
    {"code": "19-2031.00", "title": "Chemists"},
    {"code": "29-1011.00", "title": "Chiropractors"},
    {"code": "53-2012.00", "title": "Commercial Pilots"},
    {"code": "13-1041.00", "title": "Compliance Officers"},
    {"code": "39-6012.00", "title": "Concierges"},
    {"code": "19-1031.00", "title": "Conservation Scientists"},
    {"code": "15-1254.00", "title": "Web Developers"},
    {"code": "39-9011.00", "title": "Childcare Workers"},
    {"code": "11-1011.00", "title": "Chief Executives"},
    {"code": "15-2011.00", "title": "Actuaries"},
)


def load_local_environment(path: Path = LOCAL_ENV_PATH):
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        if key:
            os.environ.setdefault(key, value)


def _build_search_icon():
    return ft.Image(
        src=SEARCH_ICON_SVG.encode("utf-8"),
        width=24,
        height=24,
        color=ft.Colors.WHITE,
    )


def _build_close_icon():
    return ft.Image(
        src=CLOSE_ICON_SVG.encode("utf-8"),
        width=24,
        height=24,
        color=ft.Colors.WHITE_70,
    )


class _CardCapturePage:
    """Collect the card added by one of the standalone demo modules."""

    def __init__(self):
        self.controls = []

    def add(self, *controls):
        self.controls.extend(controls)


def _build_demo_card(module_name: str):
    demo_module = import_module(module_name)
    capture_page = _CardCapturePage()
    demo_module.main(capture_page)

    if len(capture_page.controls) != 1:
        raise RuntimeError(
            f"{module_name}.py must add exactly one root control."
        )

    root_control = capture_page.controls[0]

    if not isinstance(root_control, ft.SafeArea):
        raise RuntimeError(
            f"{module_name}.py must wrap its card in ft.SafeArea."
        )

    return root_control.content


def build_occupation_row(
    page: ft.Page,
    risk_card,
    skills_card,
    market_card,
    economics_row,
    occupation_service: OccupationService,
    gemini_risk_service: GeminiRiskService,
):
    occupation_chips = []
    occupation_chips_by_code = {}
    selected_occupation_chip = None

    def create_occupation_label(
        occupation: str,
        color=CHIP_TEXT,
    ):
        return ft.Text(
            occupation,
            size=14,
            color=color,
            weight=ft.FontWeight.W_500,
            no_wrap=True,
            offset=ft.Offset(0, 0),
            animate_offset=ft.Animation(
                duration=240,
                curve=ft.AnimationCurve.EASE_OUT,
            ),
        )

    def apply_selected_chip_style(selected_chip: ft.Container):
        for chip in occupation_chips:
            chip.bgcolor = CHIP_BG
            chip.border = ft.Border.all(
                width=1,
                color=CHIP_BORDER,
            )
            chip.content.color = CHIP_TEXT
            chip.content.weight = ft.FontWeight.W_500

        selected_chip.bgcolor = CHIP_SELECTED_BG
        selected_chip.border = ft.Border.all(
            width=1,
            color=CHIP_SELECTED_BG,
        )
        selected_chip.content.color = CHIP_SELECTED_TEXT
        selected_chip.content.weight = ft.FontWeight.W_500

    async def update_occupation_content(occupation: dict[str, str]):
        risk_task = asyncio.create_task(
            gemini_risk_service.analyze_occupation(
                occupation["title"],
            )
        )

        try:
            occupation_data = await occupation_service.get_occupation(
                occupation["code"],
                occupation["title"],
            )
        except (OnetServiceError, OewsDataError, ValueError):
            if not risk_task.done():
                risk_task.cancel()
            skills_card.set_message(
                "Unable to load occupation data. Please try again."
            )
            market_card.set_wage_history([])
            page.update()
            await asyncio.gather(
                economics_row.set_occupation(
                    None,
                    None,
                ),
                market_card.animate_current_value(),
            )
            return

        skills_card.set_skills(occupation_data["skills"])
        wage_history = occupation_data["median_wages"]
        market_card.set_wage_history(wage_history)
        page.update()

        latest_median_wage = (
            wage_history[-1]["median_annual_wage"]
            if wage_history
            else None
        )

        try:
            risk_prediction = await risk_task
        except GeminiRiskServiceError:
            risk_prediction = {
                "risk_score": 0,
                "realizable_automation_share": None,
                "tasks": [
                    {
                        "task": "Gemini analysis unavailable",
                        "probability": 0,
                        "justification": "",
                    }
                ],
            }

        risk_card.set_tasks(risk_prediction["tasks"])
        skills_card.set_plot_color(
            risk_card.color_for_score(
                risk_prediction["risk_score"]
            )
        )
        page.update(skills_card)

        await asyncio.gather(
            risk_card.set_score(
                risk_prediction["risk_score"]
            ),
            risk_card.animate_tasks(),
            economics_row.set_occupation(
                latest_median_wage,
                risk_prediction.get(
                    "realizable_automation_share"
                ),
            ),
            market_card.animate_current_value(),
        )

    async def select_occupation(
        occupation: dict[str, str],
        selected_chip: ft.Container,
    ):
        nonlocal selected_occupation_chip

        selected_occupation_chip = selected_chip
        apply_selected_chip_style(selected_chip)
        skills_card.set_loading("Loading O*NET skills…")
        risk_card.set_tasks([])
        page.update()
        await update_occupation_content(occupation)

    def create_occupation_chip(occupation: dict[str, str]):
        chip = ft.Container(
            height=46,
            alignment=ft.Alignment.CENTER_LEFT,
            padding=ft.Padding.symmetric(
                horizontal=14,
                vertical=4,
            ),
            bgcolor=CHIP_BG,
            border_radius=14,
            border=ft.Border.all(
                width=1,
                color=CHIP_BORDER,
            ),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            data=dict(occupation),
            content=create_occupation_label(occupation["title"]),
            animate=ft.Animation(
                duration=300,
                curve=ft.AnimationCurve.EASE_OUT,
            ),
            animate_size=ft.Animation(
                duration=300,
                curve=ft.AnimationCurve.EASE_OUT,
            ),
        )

        async def handle_occupation_click(
            event,
            control=chip,
        ):
            record = control.data
            if isinstance(record, dict):
                await select_occupation(dict(record), control)

        chip.on_click = handle_occupation_click
        return chip

    for occupation in DEFAULT_OCCUPATIONS:
        chip = create_occupation_chip(occupation)
        occupation_chips.append(chip)
        occupation_chips_by_code[occupation["code"]] = chip

    selected_occupation_chip = occupation_chips_by_code[
        DEFAULT_OCCUPATIONS[0]["code"]
    ]
    apply_selected_chip_style(selected_occupation_chip)

    occupation_list = ft.ListView(
        expand=True,
        horizontal=True,
        height=46,
        spacing=10,
        build_controls_on_demand=False,
        scroll=ft.Scrollbar(
            thickness=0,
            interactive=False,
            thumb_visibility=False,
            track_visibility=False,
        ),
        controls=occupation_chips,
    )

    async def scroll_occupations_left(_):
        await occupation_list.scroll_to(
            delta=-320,
            duration=250,
            curve=ft.AnimationCurve.EASE_OUT,
        )

    async def scroll_occupations_right(_):
        await occupation_list.scroll_to(
            delta=320,
            duration=250,
            curve=ft.AnimationCurve.EASE_OUT,
        )

    left_arrow = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        icon_color=CHIP_TEXT,
        icon_size=22,
        width=34,
        height=46,
        padding=0,
        on_click=scroll_occupations_left,
    )
    right_arrow = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        icon_color=CHIP_TEXT,
        icon_size=22,
        width=34,
        height=46,
        padding=0,
        on_click=scroll_occupations_right,
    )

    occupation_row = ft.Container(
        height=62,
        padding=ft.Padding.symmetric(horizontal=PAGE_PADDING),
        alignment=ft.Alignment.CENTER,
        content=ft.Row(
            height=46,
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                left_arrow,
                occupation_list,
                right_arrow,
            ],
        ),
    )

    async def replace_occupation_chip(
        chip: ft.Container,
        occupation: dict[str, str],
    ):
        label = chip.content
        label.offset = ft.Offset(0, -3)
        page.update(label)
        await asyncio.sleep(0.24)

        previous_record = chip.data
        previous_code = (
            previous_record.get("code")
            if isinstance(previous_record, dict)
            else None
        )
        if occupation_chips_by_code.get(previous_code) is chip:
            occupation_chips_by_code.pop(previous_code)

        label.animate_offset = None
        label.offset = ft.Offset(0, 3)
        chip.data = dict(occupation)
        label.value = occupation["title"]
        page.update(label)
        await asyncio.sleep(0.02)

        label.animate_offset = ft.Animation(
            duration=240,
            curve=ft.AnimationCurve.EASE_OUT,
        )
        label.offset = ft.Offset(0, 0)
        occupation_chips_by_code[occupation["code"]] = chip
        page.update(label)
        await asyncio.sleep(0.24)

    async def select_occupation_record(
        occupation: dict[str, str],
    ):
        code = occupation.get("code", "").strip()
        title = occupation.get("title", "").strip()
        if not code or not title:
            return

        record = {"code": code, "title": title}
        selected_chip = occupation_chips_by_code.get(code)
        if selected_chip is None:
            selected_chip = (
                selected_occupation_chip
                or occupation_chips[0]
            )
            await replace_occupation_chip(
                selected_chip,
                record,
            )

        await select_occupation(record, selected_chip)

    return occupation_row, select_occupation_record


def calculate_occupation_economics(
    median_wage: int | None,
    automation_share_percent: float | int | None,
) -> dict[str, float | None] | None:
    if (
        median_wage is None
        or automation_share_percent is None
    ):
        return None

    normalized_automation_share_percent = max(
        0.0,
        min(
            100.0,
            float(automation_share_percent),
        ),
    )
    automation_share = (
        normalized_automation_share_percent / 100.0
    )
    labor_value_replaced = (
        float(median_wage)
        * automation_share
    )
    automated_hours = (
        WORK_HOURS_PER_YEAR
        * automation_share
    )
    annual_input_tokens = (
        automated_hours
        * ASSUMED_INPUT_TOKENS_PER_AUTOMATED_HOUR
    )
    annual_output_tokens = (
        automated_hours
        * ASSUMED_OUTPUT_TOKENS_PER_AUTOMATED_HOUR
    )
    annual_model_cost = (
        annual_input_tokens
        / 1_000_000
        * GEMINI_INPUT_PRICE_PER_MILLION
        + annual_output_tokens
        / 1_000_000
        * GEMINI_OUTPUT_PRICE_PER_MILLION
    )
    median_hourly_wage = (
        float(median_wage)
        / WORK_HOURS_PER_YEAR
    )
    annual_oversight_cost = (
        automated_hours
        * ASSUMED_HUMAN_OVERSIGHT_SHARE
        * median_hourly_wage
    )
    annual_software_infra_cost = (
        ASSUMED_SOFTWARE_INFRA_ANNUAL
    )
    annual_maintenance_cost = (
        ASSUMED_IMPLEMENTATION_COST
        * ASSUMED_MAINTENANCE_RATE
    )
    annualized_implementation_cost = (
        ASSUMED_IMPLEMENTATION_COST
        / ASSUMED_IMPLEMENTATION_USEFUL_LIFE_YEARS
    )
    annual_recurring_ai_cost = (
        annual_model_cost
        + annual_software_infra_cost
        + annual_oversight_cost
        + annual_maintenance_cost
    )
    annual_ai_cost = (
        annual_recurring_ai_cost
        + annualized_implementation_cost
    )
    annual_savings = (
        labor_value_replaced
        - annual_ai_cost
    )
    replacement_ratio = (
        annual_ai_cost
        / labor_value_replaced
        * 100
        if labor_value_replaced > 0
        else None
    )
    annual_recurring_savings = (
        labor_value_replaced
        - annual_recurring_ai_cost
    )
    if annual_recurring_savings > 0:
        monthly_recurring_savings = (
            annual_recurring_savings / 12
        )
        payback_months = (
            ASSUMED_IMPLEMENTATION_COST
            / monthly_recurring_savings
        )
    else:
        monthly_recurring_savings = None
        payback_months = None

    return {
        "median_wage": float(median_wage),
        "automation_share_percent": (
            normalized_automation_share_percent
        ),
        "automation_share": automation_share,
        "labor_value_replaced": labor_value_replaced,
        "automated_hours": automated_hours,
        "annual_input_tokens": annual_input_tokens,
        "annual_output_tokens": annual_output_tokens,
        "annual_model_cost": annual_model_cost,
        "median_hourly_wage": median_hourly_wage,
        "annual_oversight_cost": annual_oversight_cost,
        "annual_software_infra_cost": annual_software_infra_cost,
        "annual_maintenance_cost": annual_maintenance_cost,
        "annualized_implementation_cost": (
            annualized_implementation_cost
        ),
        "annual_recurring_ai_cost": annual_recurring_ai_cost,
        "annual_ai_cost": annual_ai_cost,
        "annual_savings": annual_savings,
        "replacement_ratio": replacement_ratio,
        "annual_recurring_savings": annual_recurring_savings,
        "monthly_recurring_savings": monthly_recurring_savings,
        "payback_months": payback_months,
    }


def _format_occupation_economics(
    economics: dict[str, float | None] | None,
):
    if economics is None:
        return (
            ("—", "—", "—", "—", "—"),
            "Automation estimate unavailable",
        )

    labor_value_replaced = economics["labor_value_replaced"]
    annual_ai_cost = economics["annual_ai_cost"]
    annual_savings = economics["annual_savings"]
    replacement_ratio = economics["replacement_ratio"]
    payback_months = economics["payback_months"]

    labor_display = f"${labor_value_replaced:,.0f}"
    ai_cost_display = f"-${annual_ai_cost:,.0f}"
    if annual_savings > 0:
        savings_display = f"+${annual_savings:,.0f}"
    elif annual_savings < 0:
        savings_display = f"-${abs(annual_savings):,.0f}"
    else:
        savings_display = "$0"

    if replacement_ratio is None:
        ratio_display = "—"
        ratio_description = "No replaced labor value"
    else:
        ratio_display = f"{replacement_ratio:.1f}%"
        if replacement_ratio < 100:
            ratio_description = (
                f"{100 - replacement_ratio:.1f}% below "
                "replaced labor value"
            )
        elif replacement_ratio > 100:
            ratio_description = (
                f"{replacement_ratio - 100:.1f}% above "
                "replaced labor value"
            )
        else:
            ratio_description = "Equal to replaced labor value"

    payback_display = (
        f"{payback_months:.1f} months"
        if payback_months is not None
        else "No Payback"
    )

    return (
        (
            labor_display,
            ai_cost_display,
            savings_display,
            ratio_display,
            payback_display,
        ),
        ratio_description,
    )


def occupation_economics_values(
    median_wage: int | None,
    automation_share_percent: float | int | None,
):
    return _format_occupation_economics(
        calculate_occupation_economics(
            median_wage,
            automation_share_percent,
        )
    )


def build_risk_card():
    risk_module = import_module("56")

    return risk_module.QuadrantRiskCard(
        score=0,
        max_score=100,
    )


def build_skills_card():
    skills_card = _build_demo_card("main (3)")
    skills_card.height = SKILLS_CARD_HEIGHT
    return skills_card


def build_market_card(page: ft.Page):
    market_card = _build_demo_card("45")
    wage_reel = RollingFormattedNumber(
        page,
        "—",
        digit_width=18,
        digit_height=38,
        font_size=30,
        text_color=PRIMARY_TEXT,
        font_weight=ft.FontWeight.NORMAL,
    )
    market_card.attach_value_reel(wage_reel)
    return market_card


class EconomicsMetricsRow:
    def __init__(self, page: ft.Page):
        self.page = page
        economics_content = _build_demo_card("7")
        self.metric_cards = list(
            economics_content.metric_cards[1:]
        )
        self.current_display_values = (
            "—",
            "—",
            "—",
            "—",
            "—",
        )
        self.current_economics = None
        self.active_metric_index = None
        self.source_geometry = None
        self.is_animating = False
        self._active_source_card = None
        self.metric_titles = tuple(
            card.content.controls[2].value
            for card in self.metric_cards
        )
        self.current_descriptions = tuple(
            card.content.controls[6].value
            for card in self.metric_cards
        )
        self.value_reels = []
        self.metric_hosts = []

        for metric_index, (card, initial_value) in enumerate(zip(
            self.metric_cards,
            self.current_display_values,
            strict=True,
        )):
            value_reel = RollingFormattedNumber(
                page,
                initial_value,
                digit_width=17,
                digit_height=38,
                font_size=29,
                text_color=PRIMARY_TEXT,
                font_weight=ft.FontWeight.NORMAL,
                positive_color=METRIC_GREEN,
                negative_color=METRIC_RED,
            )
            self.value_reels.append(value_reel)

            card.width = None
            card.height = METRIC_CARD_HEIGHT
            card.expand = True
            card.padding = ft.Padding.symmetric(
                horizontal=22,
                vertical=3,
            )
            card.content.controls[0].visible = False
            card.content.controls[2].size = 12
            card.content.controls[4] = value_reel.control
            card.animate_opacity = ft.Animation(
                duration=100,
                curve=ft.AnimationCurve.EASE_OUT,
            )

            async def handle_metric_tap(
                event,
                index=metric_index,
            ):
                await self.open_metric_details(index, event)

            self.metric_hosts.append(
                ft.GestureDetector(
                    expand=True,
                    mouse_cursor=ft.MouseCursor.CLICK,
                    on_tap_down=handle_metric_tap,
                    content=card,
                )
            )

        self.control = ft.Row(
            height=METRIC_CARD_HEIGHT,
            spacing=12,
            controls=self.metric_hosts,
        )
        self.overlay = self._build_overlay()

    def _build_overlay(self):
        self._expanded_title = ft.Text(
            size=18,
            weight=ft.FontWeight.BOLD,
            color=PRIMARY_TEXT,
            expand=True,
        )
        self._expanded_value = ft.Text(
            size=34,
            weight=ft.FontWeight.W_500,
            color=PRIMARY_TEXT,
        )
        self._expanded_description = ft.Text(
            size=12,
            color=SECONDARY_TEXT,
        )
        self._expanded_details = ft.Column(
            expand=True,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        )
        self._details_host = ft.Container(
            expand=True,
            opacity=0,
            animate_opacity=ft.Animation(
                duration=140,
                curve=ft.AnimationCurve.EASE_OUT,
            ),
            content=self._expanded_details,
        )
        self._backdrop = ft.Container(
            expand=True,
            bgcolor="#99000000",
            blur=ft.Blur(12, 12),
            opacity=0,
            animate_opacity=ft.Animation(
                duration=260,
                curve=ft.AnimationCurve.EASE_OUT,
            ),
        )
        self._expanded_card = ft.Container(
            left=0,
            top=0,
            width=1,
            height=METRIC_CARD_HEIGHT,
            bgcolor=self.metric_cards[0].bgcolor,
            border=self.metric_cards[0].border,
            border_radius=self.metric_cards[0].border_radius,
            padding=ft.Padding.all(22),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            animate_position=ft.Animation(
                duration=360,
                curve=ft.AnimationCurve.EASE_OUT_CUBIC,
            ),
            animate_size=ft.Animation(
                duration=360,
                curve=ft.AnimationCurve.EASE_OUT_CUBIC,
            ),
            content=ft.Column(
                expand=True,
                spacing=9,
                controls=[
                    ft.Row(
                        spacing=8,
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                        controls=[
                            self._expanded_title,
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=PRIMARY_TEXT,
                                icon_size=20,
                                tooltip="Close",
                                on_click=self.close_expanded_metric,
                            ),
                        ],
                    ),
                    self._expanded_value,
                    self._expanded_description,
                    ft.Divider(height=1, color=CHIP_BORDER),
                    self._details_host,
                ],
            ),
        )
        overlay_stack = ft.Stack(
            expand=True,
            fit=ft.StackFit.EXPAND,
            controls=[
                self._backdrop,
                self._expanded_card,
            ],
        )
        return ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            visible=False,
            ignore_interactions=True,
            content=overlay_stack,
        )

    @staticmethod
    def _money(value: float | None) -> str:
        return "—" if value is None else f"${value:,.0f}"

    @staticmethod
    def _signed_money(value: float | None) -> str:
        if value is None:
            return "—"
        if value > 0:
            return f"+${value:,.0f}"
        if value < 0:
            return f"-${abs(value):,.0f}"
        return "$0"

    @staticmethod
    def _section_label(label: str):
        return ft.Text(
            label,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=SECONDARY_TEXT,
        )

    @staticmethod
    def _detail_row(
        label: str,
        value: str,
        *,
        value_color=PRIMARY_TEXT,
        bold=False,
    ):
        return ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Text(
                    label,
                    size=12,
                    color=SECONDARY_TEXT,
                    expand=True,
                ),
                ft.Text(
                    value,
                    size=12,
                    color=value_color,
                    weight=(
                        ft.FontWeight.BOLD
                        if bold
                        else ft.FontWeight.NORMAL
                    ),
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
        )

    @staticmethod
    def _calculation_block(*lines: str):
        return ft.Container(
            bgcolor="#111111",
            border=ft.Border.all(width=1, color=CHIP_BORDER),
            border_radius=10,
            padding=ft.Padding.all(14),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(
                        line,
                        size=12,
                        color=(
                            PRIMARY_TEXT
                            if index == len(lines) - 1
                            else SECONDARY_TEXT
                        ),
                        weight=(
                            ft.FontWeight.BOLD
                            if index == len(lines) - 1
                            else ft.FontWeight.NORMAL
                        ),
                    )
                    for index, line in enumerate(lines)
                ],
            ),
        )

    def _metric_value_color(self, metric_index: int):
        economics = self.current_economics
        if metric_index == 1:
            return METRIC_RED
        if economics is None:
            return PRIMARY_TEXT
        if metric_index == 2:
            return (
                METRIC_GREEN
                if economics["annual_savings"] >= 0
                else METRIC_RED
            )
        if metric_index == 3:
            replacement_ratio = economics["replacement_ratio"]
            if replacement_ratio is None:
                return PRIMARY_TEXT
            return (
                METRIC_GREEN
                if replacement_ratio < 100
                else METRIC_RED
                if replacement_ratio > 100
                else PRIMARY_TEXT
            )
        if metric_index == 4:
            return (
                METRIC_GREEN
                if economics["payback_months"] is not None
                else METRIC_RED
            )
        return PRIMARY_TEXT

    def _build_metric_details(self, metric_index: int):
        economics = self.current_economics
        if economics is None:
            return [
                ft.Container(
                    padding=ft.Padding.only(top=22),
                    content=ft.Text(
                        "Detailed economics are unavailable for this "
                        "occupation.",
                        size=13,
                        color=SECONDARY_TEXT,
                    ),
                )
            ]

        median_wage = economics["median_wage"]
        automation_percent = economics[
            "automation_share_percent"
        ]
        labor_value = economics["labor_value_replaced"]
        automated_hours = economics["automated_hours"]
        annual_ai_cost = economics["annual_ai_cost"]
        recurring_cost = economics["annual_recurring_ai_cost"]
        recurring_savings = economics["annual_recurring_savings"]

        if metric_index == 0:
            return [
                self._section_label("INPUTS"),
                self._detail_row(
                    "Median annual wage",
                    self._money(median_wage),
                ),
                self._detail_row(
                    "Realizable automation share",
                    f"{automation_percent:.1f}%",
                ),
                self._section_label("CALCULATION"),
                self._calculation_block(
                    f"{self._money(median_wage)} × "
                    f"{automation_percent:.1f}%",
                    f"= {self._money(labor_value)}",
                ),
                self._detail_row(
                    "Automated workload",
                    f"{automated_hours:,.0f} hours / year",
                ),
                self._calculation_block(
                    f"{WORK_HOURS_PER_YEAR:,} × "
                    f"{automation_percent:.1f}%",
                    f"= {automated_hours:,.0f} hours",
                ),
            ]

        if metric_index == 1:
            return [
                self._section_label("COST BREAKDOWN"),
                self._detail_row(
                    "Gemini/model API cost",
                    self._money(economics["annual_model_cost"]),
                ),
                self._detail_row(
                    "Software infrastructure",
                    self._money(
                        economics["annual_software_infra_cost"]
                    ),
                ),
                self._detail_row(
                    "Human oversight",
                    self._money(economics["annual_oversight_cost"]),
                ),
                self._detail_row(
                    "Maintenance",
                    self._money(economics["annual_maintenance_cost"]),
                ),
                self._detail_row(
                    "Annualized implementation",
                    self._money(
                        economics["annualized_implementation_cost"]
                    ),
                ),
                ft.Divider(height=1, color=CHIP_BORDER),
                self._detail_row(
                    "Total Annual AI Cost",
                    self._money(annual_ai_cost),
                    value_color=METRIC_RED,
                    bold=True,
                ),
                self._section_label("MODEL USAGE"),
                self._detail_row(
                    "Automated hours / year",
                    f"{automated_hours:,.0f}",
                ),
                self._detail_row(
                    "Input tokens / automated hour",
                    f"{ASSUMED_INPUT_TOKENS_PER_AUTOMATED_HOUR:,}",
                ),
                self._detail_row(
                    "Output tokens / automated hour",
                    f"{ASSUMED_OUTPUT_TOKENS_PER_AUTOMATED_HOUR:,}",
                ),
                self._detail_row(
                    "Annual input tokens",
                    f"{economics['annual_input_tokens'] / 1_000_000:.2f}M",
                ),
                self._detail_row(
                    "Annual output tokens",
                    f"{economics['annual_output_tokens'] / 1_000_000:.2f}M",
                ),
                self._detail_row(
                    "Input model rate",
                    f"${GEMINI_INPUT_PRICE_PER_MILLION:.2f} / 1M tokens",
                ),
                self._detail_row(
                    "Output model rate",
                    f"${GEMINI_OUTPUT_PRICE_PER_MILLION:.2f} / 1M tokens",
                ),
            ]

        if metric_index == 2:
            savings = economics["annual_savings"]
            return [
                self._section_label("CALCULATION"),
                self._detail_row(
                    "Labor value replaced",
                    self._signed_money(labor_value),
                    value_color=METRIC_GREEN,
                ),
                self._detail_row(
                    "Annual AI cost",
                    f"-{self._money(annual_ai_cost)}",
                    value_color=METRIC_RED,
                ),
                ft.Divider(height=1, color=CHIP_BORDER),
                self._detail_row(
                    "Net annual savings",
                    self._signed_money(savings),
                    value_color=(
                        METRIC_GREEN if savings >= 0 else METRIC_RED
                    ),
                    bold=True,
                ),
                self._section_label("RECURRING ECONOMICS"),
                self._detail_row(
                    "Annual recurring AI cost",
                    self._money(recurring_cost),
                ),
                self._detail_row(
                    "Annual recurring savings",
                    self._signed_money(recurring_savings),
                    value_color=(
                        METRIC_GREEN
                        if recurring_savings >= 0
                        else METRIC_RED
                    ),
                ),
                ft.Text(
                    "Recurring savings exclude annualized "
                    "implementation cost.",
                    size=11,
                    color=SECONDARY_TEXT,
                ),
            ]

        if metric_index == 3:
            replacement_ratio = economics["replacement_ratio"]
            _, ratio_description = _format_occupation_economics(
                economics
            )
            ratio_display = (
                f"{replacement_ratio:.1f}%"
                if replacement_ratio is not None
                else "—"
            )
            return [
                self._section_label("CALCULATION"),
                self._detail_row(
                    "Annual AI cost",
                    self._money(annual_ai_cost),
                ),
                self._detail_row(
                    "Labor value replaced",
                    self._money(labor_value),
                ),
                self._calculation_block(
                    f"{self._money(annual_ai_cost)}",
                    "──────────── × 100",
                    f"{self._money(labor_value)}",
                    f"= {ratio_display}",
                ),
                ft.Text(
                    ratio_description,
                    size=12,
                    color=self._metric_value_color(metric_index),
                    weight=ft.FontWeight.BOLD,
                ),
            ]

        monthly_savings = economics["monthly_recurring_savings"]
        payback_months = economics["payback_months"]
        controls = [
            self._section_label("INPUTS"),
            self._detail_row(
                "Upfront implementation cost",
                self._money(float(ASSUMED_IMPLEMENTATION_COST)),
            ),
            self._detail_row(
                "Annual recurring AI cost",
                self._money(recurring_cost),
            ),
            self._detail_row(
                "Labor value replaced",
                self._money(labor_value),
            ),
            self._detail_row(
                "Annual recurring savings",
                self._signed_money(recurring_savings),
            ),
            self._detail_row(
                "Monthly recurring savings",
                self._signed_money(monthly_savings),
            ),
            self._section_label("CALCULATION"),
        ]
        if payback_months is None or monthly_savings is None:
            controls.append(
                self._calculation_block(
                    "No Payback",
                    "Recurring AI cost meets or exceeds the "
                    "estimated labor value replaced.",
                )
            )
        else:
            controls.append(
                self._calculation_block(
                    self._money(float(ASSUMED_IMPLEMENTATION_COST)),
                    "───────────────",
                    f"{self._money(monthly_savings)} / month",
                    f"= {payback_months:.1f} months",
                )
            )
        return controls

    def _populate_expanded_metric(self, metric_index: int):
        self._expanded_title.value = self.metric_titles[metric_index]
        self._expanded_value.value = self.current_display_values[
            metric_index
        ]
        self._expanded_value.color = self._metric_value_color(
            metric_index
        )
        self._expanded_description.value = (
            self.current_descriptions[metric_index]
        )
        self._expanded_details.controls = (
            self._build_metric_details(metric_index)
        )

    def _compact_card_width(self):
        page_width = float(self.page.width or 1280)
        left_column_width = max(
            0.0,
            page_width
            - (PAGE_PADDING * 2)
            - RIGHT_COLUMN_WIDTH
            - CARD_GAP,
        )
        return max(
            120.0,
            (left_column_width - (12 * 4)) / 5,
        )

    def _source_card_geometry(self, metric_index: int, event):
        source_width = self._compact_card_width()
        global_position = getattr(event, "global_position", None)
        local_position = getattr(event, "local_position", None)
        if global_position is not None and local_position is not None:
            source_left = global_position.x - local_position.x
            source_top = global_position.y - local_position.y
        else:
            source_left = (
                PAGE_PADDING
                + metric_index * (source_width + 12)
            )
            source_top = 56 + 62 + PAGE_PADDING
        return (
            float(source_left),
            float(source_top),
            source_width,
            float(METRIC_CARD_HEIGHT),
        )

    def _expanded_geometry(self):
        page_width = float(self.page.width or 1280)
        page_height = float(self.page.height or 800)
        expanded_width = max(
            280.0,
            min(720.0, page_width - 40),
        )
        expanded_height = max(
            320.0,
            min(520.0, page_height - 60),
        )
        return (
            max(20.0, (page_width - expanded_width) / 2),
            max(20.0, (page_height - expanded_height) / 2),
            expanded_width,
            expanded_height,
        )

    async def open_metric_details(self, metric_index: int, event):
        if self.active_metric_index is not None or self.is_animating:
            return

        self.is_animating = True
        self.active_metric_index = metric_index
        self._active_source_card = self.metric_cards[metric_index]
        self.source_geometry = self._source_card_geometry(
            metric_index,
            event,
        )
        source_left, source_top, source_width, source_height = (
            self.source_geometry
        )
        self._populate_expanded_metric(metric_index)
        self._details_host.opacity = 0
        self._backdrop.opacity = 0
        self._expanded_card.left = source_left
        self._expanded_card.top = source_top
        self._expanded_card.width = source_width
        self._expanded_card.height = source_height
        self._expanded_card.animate_position = ft.Animation(
            duration=360,
            curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        )
        self._expanded_card.animate_size = ft.Animation(
            duration=360,
            curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        )
        self.overlay.ignore_interactions = False
        self.overlay.visible = True
        self.page.update(self.overlay)
        await asyncio.sleep(0.02)

        target_left, target_top, target_width, target_height = (
            self._expanded_geometry()
        )
        self._active_source_card.opacity = 0
        self._backdrop.opacity = 1
        self._expanded_card.left = target_left
        self._expanded_card.top = target_top
        self._expanded_card.width = target_width
        self._expanded_card.height = target_height
        self.page.update(
            self._active_source_card,
            self._backdrop,
            self._expanded_card,
        )
        await asyncio.sleep(0.38)

        self._populate_expanded_metric(metric_index)
        self._details_host.opacity = 1
        self.page.update(
            self._expanded_title,
            self._expanded_value,
            self._expanded_description,
            self._expanded_details,
            self._details_host,
        )
        self.is_animating = False

    async def close_expanded_metric(self, _):
        if self.active_metric_index is None or self.is_animating:
            return

        self.is_animating = True
        self._details_host.opacity = 0
        self.page.update(self._details_host)
        await asyncio.sleep(0.12)

        source_left, source_top, source_width, source_height = (
            self.source_geometry
        )
        self._expanded_card.animate_position = ft.Animation(
            duration=320,
            curve=ft.AnimationCurve.EASE_IN_CUBIC,
        )
        self._expanded_card.animate_size = ft.Animation(
            duration=320,
            curve=ft.AnimationCurve.EASE_IN_CUBIC,
        )
        self._expanded_card.left = source_left
        self._expanded_card.top = source_top
        self._expanded_card.width = source_width
        self._expanded_card.height = source_height
        self._backdrop.opacity = 0
        self.page.update(self._expanded_card, self._backdrop)
        await asyncio.sleep(0.34)

        self._active_source_card.opacity = 1
        self.overlay.visible = False
        self.overlay.ignore_interactions = True
        self.page.update(self._active_source_card, self.overlay)
        self.active_metric_index = None
        self._active_source_card = None
        self.source_geometry = None
        self.is_animating = False

    async def initialize(self):
        await asyncio.gather(
            *[
                value_reel.initialize()
                for value_reel in self.value_reels
            ]
        )

    async def set_occupation(
        self,
        median_wage: int | None,
        automation_share_percent: float | int | None,
    ):
        self.current_economics = calculate_occupation_economics(
            median_wage,
            automation_share_percent,
        )
        display_values, ratio_description = (
            _format_occupation_economics(
                self.current_economics
            )
        )
        self.current_display_values = display_values
        payback_description = (
            "Upfront implementation ÷ monthly recurring savings"
            if (
                self.current_economics is not None
                and self.current_economics["payback_months"]
                is not None
            )
            else (
                "Recurring AI cost meets or exceeds replaced "
                "labor value"
                if self.current_economics is not None
                else "Automation estimate unavailable"
            )
        )
        self.current_descriptions = (
            "Median wage × realizable automation share",
            "API + software + oversight + maintenance "
            "+ annualized implementation",
            "Labor value replaced − annual AI cost",
            ratio_description,
            payback_description,
        )
        ratio_description_control = (
            self.metric_cards[3].content.controls[6]
        )
        ratio_description_control.value = ratio_description
        payback_description_control = (
            self.metric_cards[4].content.controls[6]
        )
        payback_description_control.value = payback_description
        self.page.update(
            ratio_description_control,
            payback_description_control,
        )

        await asyncio.gather(
            *[
                value_reel.set_text(display_value)
                for value_reel, display_value in zip(
                    self.value_reels,
                    display_values,
                    strict=True,
                )
            ]
        )
        if self.active_metric_index is not None:
            self._populate_expanded_metric(
                self.active_metric_index
            )
            self.page.update(
                self._expanded_title,
                self._expanded_value,
                self._expanded_description,
                self._expanded_details,
            )


def build_dashboard(
    risk_card,
    skills_card,
    market_card,
    economics_row,
):
    market_card.width = None
    risk_card.width = RIGHT_COLUMN_WIDTH
    skills_card.width = RIGHT_COLUMN_WIDTH

    right_column = ft.Column(
        width=RIGHT_COLUMN_WIDTH,
        spacing=RIGHT_CARD_GAP,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            risk_card,
            skills_card,
        ],
    )

    left_column = ft.Column(
        expand=True,
        spacing=16,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            economics_row.control,
            market_card,
        ],
    )

    return ft.Row(
        spacing=CARD_GAP,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            left_column,
            right_column,
        ],
    )


async def main(page: ft.Page):
    load_local_environment()

    page.title = "Career Insights Dashboard"
    page.bgcolor = PAGE_BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    app_bar = ft.Container(
        height=56,
        bgcolor=APPBAR_BG,
        padding=ft.Padding.only(left=16, right=16),
        alignment=ft.Alignment.CENTER_LEFT,
        content=ft.Text(
            "ΛIM ",
            size=18,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.WHITE,
        ),
    )

    risk_card = build_risk_card()
    skills_card = build_skills_card()
    market_card = build_market_card(page)
    economics_row = EconomicsMetricsRow(page)
    onet_service = OnetService()
    gemini_risk_service = GeminiRiskService()
    occupation_service = OccupationService(
        onet_service,
        OewsWageService(),
    )
    occupation_row, select_occupation = build_occupation_row(
        page,
        risk_card,
        skills_card,
        market_card,
        economics_row,
        occupation_service,
        gemini_risk_service,
    )
    search_control = await occupation_search.main(
        page,
        occupations=[],
        search_provider=onet_service.search_occupations,
        on_select=select_occupation,
        mount=False,
        show_selection_text=False,
        collapse_on_select=True,
        search_button_bgcolor=ft.Colors.BLACK,
        expanded_search_button_bgcolor="#202124",
        search_button_size=48,
        search_height=48,
        collapsed_width=48,
        search_button_icon=_build_search_icon(),
        search_result_icon_factory=_build_search_icon,
        clear_button_icon=_build_close_icon(),
    )
    search_control.horizontal_alignment = (
        ft.CrossAxisAlignment.END
    )
    dashboard = build_dashboard(
        risk_card,
        skills_card,
        market_card,
        economics_row,
    )

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Stack(
                expand=True,
                controls=[
                    ft.Column(
                        expand=True,
                        spacing=0,
                        horizontal_alignment=(
                            ft.CrossAxisAlignment.STRETCH
                        ),
                        controls=[
                            app_bar,
                            ft.Column(
                                expand=True,
                                spacing=0,
                                horizontal_alignment=(
                                    ft.CrossAxisAlignment.STRETCH
                                ),
                                scroll=ft.ScrollMode.AUTO,
                                controls=[
                                    occupation_row,
                                    ft.Container(
                                        padding=ft.Padding.all(
                                            PAGE_PADDING
                                        ),
                                        content=dashboard,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Container(
                        top=7,
                        right=PAGE_PADDING,
                        width=occupation_search.EXPANDED_WIDTH,
                        content=search_control,
                    ),
                    economics_row.overlay,
                ],
            ),
        )
    )

    await asyncio.gather(
        economics_row.initialize(),
        market_card.initialize_value_reel(),
    )

    await select_occupation(DEFAULT_OCCUPATIONS[0])


if __name__ == "__main__":
    ft.run(main,view=ft.AppView.WEB_BROWSER)
