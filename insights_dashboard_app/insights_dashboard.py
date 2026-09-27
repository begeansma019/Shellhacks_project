import asyncio
import hashlib
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
                    occupation["title"],
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
                "tasks": [
                    {
                        "task": "Gemini analysis unavailable",
                        "probability": 0,
                        "justification": "",
                    }
                ],
            }

        risk_card.set_tasks(risk_prediction["tasks"])

        await asyncio.gather(
            risk_card.set_score(
                risk_prediction["risk_score"]
            ),
            risk_card.animate_tasks(),
            economics_row.set_occupation(
                occupation_data["title"],
                latest_median_wage,
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
            data=dict(occupation),
            content=create_occupation_label(occupation["title"]),
            animate=ft.Animation(
                duration=300,
                curve=ft.AnimationCurve.EASE_OUT,
            ),
        )

        async def handle_occupation_click(
            event,
            record=dict(occupation),
            control=chip,
        ):
            await select_occupation(record, control)

        chip.on_click = handle_occupation_click
        return chip

    for occupation in DEFAULT_OCCUPATIONS:
        chip = create_occupation_chip(occupation)
        occupation_chips.append(chip)
        occupation_chips_by_code[occupation["code"]] = chip

    occupation_list = ft.ListView(
        horizontal=True,
        height=46,
        spacing=10,
        scroll=ft.Scrollbar(
            thickness=0,
            interactive=False,
            thumb_visibility=False,
            track_visibility=False,
        ),
        controls=occupation_chips,
    )
    occupation_row = ft.Container(
        height=62,
        padding=ft.Padding.symmetric(horizontal=PAGE_PADDING),
        alignment=ft.Alignment.CENTER,
        content=occupation_list,
    )

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
            selected_chip = create_occupation_chip(record)
            occupation_chips.append(selected_chip)
            occupation_chips_by_code[code] = selected_chip
            page.update(occupation_list)

        await select_occupation(record, selected_chip)

    return occupation_row, select_occupation_record


def occupation_economics_values(
    occupation: str,
    labor_value: int | None,
):
    if labor_value is None:
        return (
            ("—", "—", "—", "—", "—"),
            "Median wage unavailable",
        )

    digest = hashlib.sha256(
        f"economics:{occupation}".encode("utf-8")
    ).digest()
    ratio_tenths = (
        250
        + int.from_bytes(digest[2:4], "big") % 451
    )
    annual_ai_cost = round(
        labor_value * ratio_tenths / 1_000
    )
    annual_savings = labor_value - annual_ai_cost
    payback_tenths = (
        25
        + int.from_bytes(digest[4:6], "big") % 65
    )
    replacement_ratio = ratio_tenths / 10

    return (
        (
            f"${labor_value:,.0f}",
            f"-${annual_ai_cost:,.0f}",
            f"+${annual_savings:,.0f}",
            f"{replacement_ratio:.1f}%",
            f"{payback_tenths / 10:.1f} months",
        ),
        f"{100 - replacement_ratio:.1f}% below labor cost",
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
        initial_values = (
            "—",
            "—",
            "—",
            "—",
            "—",
        )
        self.value_reels = []

        for card, initial_value in zip(
            self.metric_cards,
            initial_values,
            strict=True,
        ):
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

        self.control = ft.Row(
            height=METRIC_CARD_HEIGHT,
            spacing=12,
            controls=self.metric_cards,
        )

    async def initialize(self):
        await asyncio.gather(
            *[
                value_reel.initialize()
                for value_reel in self.value_reels
            ]
        )

    async def set_occupation(
        self,
        occupation: str,
        median_wage: int | None,
    ):
        display_values, ratio_description = (
            occupation_economics_values(
                occupation,
                median_wage,
            )
        )
        ratio_description_control = (
            self.metric_cards[3].content.controls[6]
        )
        ratio_description_control.value = ratio_description
        self.page.update(ratio_description_control)

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
            "Career Insights Dashboard",
            size=18,
            weight=ft.FontWeight.W_600,
            color=PRIMARY_TEXT,
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
