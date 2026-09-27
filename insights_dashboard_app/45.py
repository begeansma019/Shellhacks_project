import base64
import math

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
CHATGPT_RELEASE_LOGO = base64.b64decode(
    (
        "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"
    )
)


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
