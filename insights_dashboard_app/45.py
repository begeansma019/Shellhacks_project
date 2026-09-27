import math
from importlib import import_module

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
OUTLOOK_AXIS_INTERVAL = 2

METRIC_WAGE = "city"
METRIC_OUTLOOK = "state"


def build_market_series(values, metric_key=METRIC_WAGE):
    return fch.LineChartData(
        points=[
            fch.LineChartDataPoint(
                index,
                value,
                tooltip=fch.LineChartDataPointTooltip(
                    text=format_current_value(metric_key, value),
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


def metric_axis_interval(metric_key, values):
    base_interval = {
        METRIC_WAGE: WAGE_AXIS_INTERVAL,
        METRIC_OUTLOOK: OUTLOOK_AXIS_INTERVAL,
    }[metric_key]

    if len(values) < 2:
        return base_interval

    span = max(values) - min(values)
    target_interval = span / 4
    if target_interval <= base_interval:
        return base_interval

    multiplier = target_interval / base_interval
    magnitude = 10 ** math.floor(math.log10(multiplier))
    normalized = multiplier / magnitude
    nice_multiplier = next(
        candidate
        for candidate in (1, 2, 5, 10)
        if normalized <= candidate
    )
    return base_interval * nice_multiplier * magnitude


def metric_axis_values(metric_key, values):
    interval = metric_axis_interval(metric_key, values)
    minimum_value = math.floor(min(values) / interval) * interval
    maximum_value = math.ceil(max(values) / interval) * interval

    if metric_key != METRIC_WAGE:
        minimum_value = max(0, minimum_value)

    interval_count = round(
        (maximum_value - minimum_value) / interval
    )
    missing_intervals = max(0, 4 - interval_count)
    lower_intervals = missing_intervals // 2
    upper_intervals = missing_intervals - lower_intervals

    if metric_key == METRIC_WAGE:
        minimum_value -= lower_intervals * interval
    else:
        available_lower_intervals = round(
            minimum_value / interval
        )
        applied_lower_intervals = min(
            lower_intervals,
            available_lower_intervals,
        )
        minimum_value -= applied_lower_intervals * interval
        upper_intervals += (
            lower_intervals - applied_lower_intervals
        )

    maximum_value += upper_intervals * interval
    interval_count = round(
        (maximum_value - minimum_value) / interval
    )
    return [
        minimum_value + index * interval
        for index in range(interval_count + 1)
    ]


def format_axis_value(metric_key, value):
    if metric_key == METRIC_WAGE:
        return f"${round(value) // 1_000}K"
    if metric_key == METRIC_OUTLOOK:
        return f"{value:g}%"
    return f"{value:g}"


def format_current_value(metric_key, value):
    if metric_key == METRIC_WAGE:
        return f"${value:,.0f}"
    if metric_key == METRIC_OUTLOOK:
        return f"{value:.1f}%"
    return f"{value:g}"


def build_metric_axis(metric_key, values, interval=None):
    if interval is None:
        interval = {
            METRIC_WAGE: WAGE_AXIS_INTERVAL,
            METRIC_OUTLOOK: OUTLOOK_AXIS_INTERVAL,
        }[metric_key]
    return fch.ChartAxis(
        label_size=40,
        label_spacing=interval,
        labels=[
            fch.ChartAxisLabel(
                value=value,
                label=ft.Text(
                    format_axis_value(metric_key, value),
                    size=10,
                    color=MUTED,
                ),
            )
            for value in values
        ],
    )


def build_timeline_axis(years):
    return fch.ChartAxis(
        label_size=30,
        labels=[
            fch.ChartAxisLabel(
                value=index,
                label=ft.Text(
                    str(year),
                    size=9,
                    color=MUTED,
                ),
            )
            for index, year in enumerate(years)
        ],
    )


class MarketTrendsCard(ft.Container):
    def __init__(
        self,
        chart: fch.LineChart,
        current_value_text: ft.Text,
        current_value_holder: ft.Container,
        trend_selector,
        metric_values,
        metric_years,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._chart = chart
        self._market_line = chart.data_series[0]
        self._current_value_text = current_value_text
        self._current_value_holder = current_value_holder
        self._trend_selector = trend_selector
        self._metric_values = {
            key: list(values)
            for key, values in metric_values.items()
        }
        self._metric_years = {
            key: list(years)
            for key, years in metric_years.items()
        }
        self._selected_metric_key = METRIC_WAGE
        self._selector_page = None
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

    def bind_metric_selector(self, page):
        self._selector_page = page
        self._trend_selector.on_location_change = (
            self._handle_metric_selection
        )

    def _handle_metric_selection(self, metric_key):
        if metric_key not in self._metric_values:
            return

        self._selected_metric_key = metric_key
        self._apply_selected_metric()

        if self._selector_page is None:
            return

        self._selector_page.update(self._chart)

        if self._value_reel is not None:
            async def animate_value():
                await self.animate_current_value()

            self._selector_page.run_task(animate_value)

    def _apply_selected_metric(self):
        values = self._metric_values[self._selected_metric_key]
        years = self._metric_years[self._selected_metric_key]
        self._market_line = build_market_series(
            values,
            self._selected_metric_key,
        )
        self._chart.data_series = [self._market_line]

        if not values:
            self._chart.min_y = 0
            self._chart.max_y = 1
            self._chart.left_axis = build_metric_axis(
                self._selected_metric_key,
                [],
            )
            self._chart.min_x = 0
            self._chart.max_x = 1
            self._chart.bottom_axis = build_timeline_axis([])
            self._target_value_text = "—"
            if self._value_reel is None:
                self._current_value_text.value = "—"
            return

        axis_values = metric_axis_values(
            self._selected_metric_key,
            values,
        )
        axis_interval = axis_values[1] - axis_values[0]
        axis_padding = axis_interval * 0.15
        self._chart.min_y = (
            axis_values[0] - axis_padding
            if self._selected_metric_key == METRIC_WAGE
            else max(0, axis_values[0] - axis_padding)
        )
        self._chart.max_y = axis_values[-1] + axis_padding
        self._chart.left_axis = build_metric_axis(
            self._selected_metric_key,
            axis_values,
            axis_interval,
        )
        self._chart.min_x = 0
        self._chart.max_x = len(values) - 1
        self._chart.bottom_axis = build_timeline_axis(years)
        self._chart.horizontal_grid_lines = fch.ChartGridLines(
            interval=axis_interval,
            width=1,
            color=GRID,
        )
        self._target_value_text = format_current_value(
            self._selected_metric_key,
            values[-1],
        )

        if self._value_reel is None:
            self._current_value_text.value = (
                self._target_value_text
            )

    def set_metric_values(self, metric_values):
        for metric_key, values in metric_values.items():
            if metric_key not in self._metric_values:
                continue
            self._metric_values[metric_key] = list(values)

        self._apply_selected_metric()

    def set_values(self, values):
        self.set_metric_values({METRIC_WAGE: values})

    def set_wage_history(self, wage_history):
        self._metric_years[METRIC_WAGE] = [
            observation["year"]
            for observation in wage_history
        ]
        self._metric_values[METRIC_WAGE] = [
            observation["median_annual_wage"]
            for observation in wage_history
        ]
        self._apply_selected_metric()


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

    market_values = []
    outlook_values = [
        5.8,
        6.2,
        6.5,
        6.9,
        7.4,
        7.9,
    ]

    # =====================================================
    # LINE SERIES
    # =====================================================

    market_line = build_market_series(
        market_values,
        METRIC_WAGE,
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

        left_axis=build_metric_axis(
            METRIC_WAGE,
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

    trend_selector_module = import_module("main (5)")
    trend_selector = (
        trend_selector_module.ExpandableLocationContainer(
            location_name="Median Wage",
            state_location="Outlook",
            national_location="",
        )
    )
    trend_selector.locations = tuple(
        option
        for option in trend_selector.locations
        if option.key != "national"
    )
    trend_selector.options_row.controls = [
        trend_selector.option_containers[option.key]
        for option in trend_selector.locations
    ]
    trend_selector.expanded_width = 300
    trend_selector.TEXT_SIZE = 16
    for option_text in trend_selector.option_text.values():
        option_text.size = trend_selector.TEXT_SIZE
        option_text.weight = ft.FontWeight.BOLD
    trend_selector.offset = ft.Offset(0, -0.08)
    trend_selector._sync(refresh=False)

    header = ft.Row(

        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,

        controls=[

            trend_selector,

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
        trend_selector=trend_selector,
        metric_values={
            METRIC_WAGE: market_values,
            METRIC_OUTLOOK: outlook_values,
        },
        metric_years={
            METRIC_WAGE: [],
            METRIC_OUTLOOK: list(range(2024, 2035, 2)),
        },

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

    if hasattr(page, "run_task"):
        market_card.bind_metric_selector(page)

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
