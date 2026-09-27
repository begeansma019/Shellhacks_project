import math
from pathlib import Path

import flet as ft
import flet_charts as fch


# =========================================================
# COLORS
# =========================================================

PAGE_BG = "#000000"
CARD_BG = "#030303"

CARD_BORDER = "#292929"

TEXT = "#E8E8E8"
MUTED = "#7F7F84"

GRID = "#1E1E20"

GREEN = "#24D36B"
WAGE_AXIS_INTERVAL = 5_000
CHATGPT_RELEASE_LOGO = (
    Path(__file__).with_name("assets")
    / "chatgpt_release_logo.png"
).read_bytes()


def build_market_series(values):
    return fch.LineChartData(
        points=[
            fch.LineChartDataPoint(
                index,
                value,
                tooltip=fch.LineChartDataPointTooltip(
                    text=format_current_value(value),
                    text_style=ft.TextStyle(
                        color=ft.Colors.WHITE,
                    ),
                ),
            )
            for index, value in enumerate(values)
        ],
        curved=True,
        curve_smoothness=0.35,
        prevent_curve_over_shooting=True,
        color=GREEN,
        stroke_width=4,
        rounded_stroke_cap=True,
        rounded_stroke_join=True,
        point=False,
        selected_below_line=fch.ChartPointLine(
            color=GREEN,
            width=1,
            dash_pattern=[4, 4],
        ),
        below_line_gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER,
            end=ft.Alignment.BOTTOM_CENTER,
            colors=[
                ft.Colors.with_opacity(0.28, GREEN),
                ft.Colors.with_opacity(0.12, GREEN),
                ft.Colors.with_opacity(0.00, GREEN),
            ],
            stops=[0.0, 0.45, 1.0],
        ),
    )


def wage_axis_interval(values):
    if len(values) < 2:
        return WAGE_AXIS_INTERVAL

    span = max(values) - min(values)
    target_interval = span / 4
    if target_interval <= WAGE_AXIS_INTERVAL:
        return WAGE_AXIS_INTERVAL

    multiplier = target_interval / WAGE_AXIS_INTERVAL
    magnitude = 10 ** math.floor(math.log10(multiplier))
    normalized = multiplier / magnitude
    nice_multiplier = next(
        candidate
        for candidate in (1, 2, 5, 10)
        if normalized <= candidate
    )
    return WAGE_AXIS_INTERVAL * nice_multiplier * magnitude


def wage_axis_values(values):
    interval = wage_axis_interval(values)
    minimum_value = math.floor(min(values) / interval) * interval
    maximum_value = math.ceil(max(values) / interval) * interval

    interval_count = round(
        (maximum_value - minimum_value) / interval
    )
    missing_intervals = max(0, 4 - interval_count)
    lower_intervals = missing_intervals // 2
    upper_intervals = missing_intervals - lower_intervals

    minimum_value -= lower_intervals * interval
    maximum_value += upper_intervals * interval
    interval_count = round(
        (maximum_value - minimum_value) / interval
    )
    return [
        minimum_value + index * interval
        for index in range(interval_count + 1)
    ]


def format_axis_value(value):
    return f"${round(value) // 1_000}K"


def format_current_value(value):
    return f"${value:,.0f}"


def build_wage_axis(values, interval=None):
    if interval is None:
        interval = WAGE_AXIS_INTERVAL
    return fch.ChartAxis(
        label_size=40,
        label_spacing=interval,
        labels=[
            fch.ChartAxisLabel(
                value=value,
                label=ft.Text(
                    format_axis_value(value),
                    size=10,
                    color=MUTED,
                ),
            )
            for value in values
        ],
    )


def build_chatgpt_release_label():
    return ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=2,
        controls=[
            ft.Text(
                "2022",
                size=9,
                color=MUTED,
            ),
            ft.Container(
                width=22,
                height=22,
                border_radius=11,
                alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(
                    width=1,
                    color="#D8D8D8",
                ),
                content=ft.Image(
                    src=CHATGPT_RELEASE_LOGO,
                    width=14,
                    height=14,
                    fit=ft.BoxFit.CONTAIN,
                    anti_alias=True,
                ),
            ),
            ft.Text(
                "ChatGPT\nreleased",
                size=8,
                color=MUTED,
                text_align=ft.TextAlign.CENTER,
                no_wrap=False,
            ),
        ],
    )


def build_timeline_axis(years):
    labels = []

    for index, year in enumerate(years):
        if year == 2022:
            label = build_chatgpt_release_label()
        else:
            label = ft.Text(
                str(year),
                size=9,
                color=MUTED,
            )

        labels.append(
            fch.ChartAxisLabel(
                value=index,
                label=label,
            )
        )

    return fch.ChartAxis(
        label_size=72,
        labels=labels,
    )


class MarketTrendsCard(ft.Container):
    def __init__(
        self,
        chart: fch.LineChart,
        current_value_text: ft.Text,
        current_value_holder: ft.Container,
        wage_values,
        wage_years,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._chart = chart
        self._market_line = chart.data_series[0]
        self._current_value_text = current_value_text
        self._current_value_holder = current_value_holder
        self._wage_values = list(wage_values)
        self._wage_years = list(wage_years)
        self._value_reel = None
        self._target_value_text = current_value_text.value

    def attach_value_reel(self, value_reel):
        self._value_reel = value_reel
        self._current_value_holder.content = value_reel.control

    async def initialize_value_reel(self):
        if self._value_reel is not None:
            await self._value_reel.initialize()

    async def animate_current_value(self):
        if self._value_reel is not None:
            await self._value_reel.set_text(
                self._target_value_text
            )

    def _apply_wage_history(self):
        self._market_line = build_market_series(self._wage_values)
        self._chart.data_series = [self._market_line]

        if not self._wage_values:
            self._chart.min_y = 0
            self._chart.max_y = 1
            self._chart.left_axis = build_wage_axis([])
            self._chart.min_x = 0
            self._chart.max_x = 1
            self._chart.bottom_axis = build_timeline_axis([])
            self._target_value_text = "—"
            if self._value_reel is None:
                self._current_value_text.value = "—"
            return

        axis_values = wage_axis_values(self._wage_values)
        axis_interval = axis_values[1] - axis_values[0]
        axis_padding = axis_interval * 0.15
        self._chart.min_y = axis_values[0] - axis_padding
        self._chart.max_y = axis_values[-1] + axis_padding
        self._chart.left_axis = build_wage_axis(
            axis_values,
            axis_interval,
        )
        self._chart.min_x = 0
        self._chart.max_x = len(self._wage_values) - 1
        self._chart.bottom_axis = build_timeline_axis(
            self._wage_years
        )
        self._chart.horizontal_grid_lines = fch.ChartGridLines(
            interval=axis_interval,
            width=1,
            color=GRID,
        )
        self._target_value_text = format_current_value(
            self._wage_values[-1],
        )

        if self._value_reel is None:
            self._current_value_text.value = (
                self._target_value_text
            )

    def set_wage_history(self, wage_history):
        self._wage_years = [
            observation["year"]
            for observation in wage_history
        ]
        self._wage_values = [
            observation["median_annual_wage"]
            for observation in wage_history
        ]
        self._apply_wage_history()


# =========================================================
# MAIN
# =========================================================

def main(page: ft.Page):

    page.title = "Market Trends"

    page.bgcolor = PAGE_BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # =====================================================
    # MARKET DATA
    # =====================================================

    wage_values = []
    wage_years = []

    # =====================================================
    # LINE SERIES
    # =====================================================

    market_line = build_market_series(
        wage_values,
    )
    initial_axis_values = []

    # =====================================================
    # LINE CHART
    # =====================================================

    chart = fch.LineChart(

        expand=True,

        animation=ft.Animation(
            duration=450,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        ),

        data_series=[
            market_line,
        ],

        min_x=0,
        max_x=1,

        min_y=0,
        max_y=1,

        bgcolor=ft.Colors.TRANSPARENT,

        border=ft.Border.only(
            left=ft.BorderSide(
                width=1,
                color=CARD_BORDER,
            ),
            bottom=ft.BorderSide(
                width=1,
                color=CARD_BORDER,
            ),
        ),

        interactive=True,

        # =================================================
        # GRID
        # =================================================

        horizontal_grid_lines=fch.ChartGridLines(
            interval=WAGE_AXIS_INTERVAL,
            width=1,
            color=GRID,
        ),

        # =================================================
        # LEFT Y AXIS
        # =================================================

        left_axis=build_wage_axis(
            initial_axis_values,
        ),

        # =================================================
        # BOTTOM X AXIS
        # =================================================

        bottom_axis=build_timeline_axis([]),

        right_axis=fch.ChartAxis(
            show_labels=False,
        ),

        top_axis=fch.ChartAxis(
            show_labels=False,
        ),

        # No visible chart border


        # =================================================
        # TOOLTIP
        # =================================================

        tooltip=fch.LineChartTooltip(

            bgcolor="#151515",

            border_radius=8,

            border_side=ft.BorderSide(
                width=1,
                color="#303030",
            ),

            fit_inside_horizontally=True,
            fit_inside_vertically=True,
        ),
    )

    # =====================================================
    # CURRENT VALUE
    # =====================================================

    current_value_text = ft.Text(
        "—",
        size=30,
        color=TEXT,
        weight=ft.FontWeight.NORMAL,
    )
    current_value_holder = ft.Container(
        alignment=ft.Alignment.CENTER_RIGHT,
        content=current_value_text,
    )

    # =====================================================
    # HEADER
    # =====================================================

    title = ft.Text(
        "Median Wage",
        size=16,
        color=TEXT,
        weight=ft.FontWeight.BOLD,
    )

    header = ft.Row(

        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,

        controls=[

            title,

            current_value_holder,
        ],
    )

    # =====================================================
    # MARKET CARD
    # =====================================================

    market_card = MarketTrendsCard(

        chart=chart,
        current_value_text=current_value_text,
        current_value_holder=current_value_holder,
        wage_values=wage_values,
        wage_years=wage_years,

        width=980,
        height=590,

        bgcolor=CARD_BG,

        border=ft.Border.all(
            width=1,
            color=CARD_BORDER,
        ),

        border_radius=20,

        padding=ft.Padding(
            left=30,
            right=30,
            top=28,
            bottom=24,
        ),

        content=ft.Column(

            spacing=0,

            controls=[

                # Header
                header,

                # Large chart area
                ft.Container(
                    expand=True,

                    padding=ft.Padding.only(
                        top=5,
                        left=0,
                        right=0,
                        bottom=0,
                    ),

                    content=chart,
                ),
            ],
        ),
    )

    # =====================================================
    # PAGE
    # =====================================================

    page.add(
        ft.SafeArea(
            content=market_card,
        )
    )


# =========================================================
# RUN
# =====================================================

if __name__ == "__main__":
    ft.run(main)
