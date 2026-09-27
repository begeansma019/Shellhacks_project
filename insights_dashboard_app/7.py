import flet as ft


class EconomicsContent(ft.Column):
    def __init__(self, metric_cards, **kwargs):
        super().__init__(**kwargs)
        self.metric_cards = metric_cards


def main(page: ft.Page):

    # ---------------------------------------------------------
    # PAGE
    # ---------------------------------------------------------

    page.title = "AI Replacement Economics"
    page.bgcolor = "#050505"
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO

    # ---------------------------------------------------------
    # COLORS
    # ---------------------------------------------------------

    BG = "#050505"
    CARD_BG = "#080808"
    BORDER = "#272727"

    TEXT_PRIMARY = "#F2F2F2"
    TEXT_SECONDARY = "#858585"
    TEXT_MUTED = "#626262"

    GREEN = "#18D66B"
    RED = "#FF4D4D"
    ORANGE = "#FF851B"

    # ---------------------------------------------------------
    # EXAMPLE VALUES
    #
    # Replace these with your actual calculated values.
    # ---------------------------------------------------------

    occupation_market_value = 75940
    labor_value_replaced = 75940

    annual_ai_cost = 26333
    annual_savings = 49607

    replacement_ratio = 34.7
    payback_months = 5.2

    # ---------------------------------------------------------
    # MONEY FORMATTER
    # ---------------------------------------------------------

    def money(value, show_sign=False):
        """
        Formats money with optional +/- sign.

        Examples:
        49607  -> +$49,607
        -5000  -> -$5,000
        """

        if show_sign:
            if value > 0:
                return f"+${abs(value):,.0f}"

            elif value < 0:
                return f"-${abs(value):,.0f}"

            else:
                return "$0"

        return f"${value:,.0f}"

    # ---------------------------------------------------------
    # SENTIMENT COLOR
    # ---------------------------------------------------------

    def sentiment_color(value):
        """
        Positive = green
        Negative = red
        Zero = white
        """

        if value > 0:
            return GREEN

        elif value < 0:
            return RED

        return TEXT_PRIMARY

    # ---------------------------------------------------------
    # METRIC CARD
    # ---------------------------------------------------------

    def metric_card(
        title,
        value,
        description,
        value_color=TEXT_PRIMARY,
        indicator_color=None,
    ):

        # Default indicator matches value color
        if indicator_color is None:
            indicator_color = value_color

        value_sign = value[:1] if value[:1] in ("+", "-") else ""

        if value_sign:
            value_control = ft.Text(
                size=29,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
                spans=[
                    ft.TextSpan(
                        text=value_sign,
                        style=ft.TextStyle(color=value_color),
                    ),
                    ft.TextSpan(text=value[1:]),
                ],
            )
        else:
            value_control = ft.Text(
                value,
                size=29,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            )

        return ft.Container(
            width=300,
            height=165,

            bgcolor=CARD_BG,

            border=ft.Border.all(
                width=1,
                color=BORDER,
            ),

            border_radius=16,
            padding=22,

            content=ft.Column(
                spacing=0,
                controls=[

                    # -----------------------------------------
                    # SENTIMENT INDICATOR
                    # -----------------------------------------

                    ft.Container(
                        width=34,
                        height=3,
                        bgcolor=indicator_color,
                        border_radius=3,
                    ),

                    ft.Container(height=15),

                    # -----------------------------------------
                    # TITLE
                    # -----------------------------------------

                    ft.Text(
                        title,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_SECONDARY,
                    ),

                    ft.Container(height=10),

                    # -----------------------------------------
                    # VALUE
                    # -----------------------------------------

                    value_control,

                    ft.Container(height=10),

                    # -----------------------------------------
                    # DESCRIPTION
                    # -----------------------------------------

                    ft.Text(
                        description,
                        size=12,
                        color=TEXT_SECONDARY,
                    ),
                ],
            ),
        )

    # ---------------------------------------------------------
    # 1. OCCUPATION MARKET VALUE
    #
    # Neutral metric
    # ---------------------------------------------------------

    market_value_card = metric_card(
        title="Occupation Market Value",
        value=money(occupation_market_value),
        description="Median annual salary",
        value_color=TEXT_PRIMARY,
        indicator_color=TEXT_MUTED,
    )

    # ---------------------------------------------------------
    # 2. LABOR VALUE REPLACED
    #
    # Neutral metric
    # ---------------------------------------------------------

    labor_replaced_card = metric_card(
        title="Labor Value Replaced",
        value=money(labor_value_replaced),
        description="Median wage × realizable automation share",
        value_color=TEXT_PRIMARY,
        indicator_color=TEXT_MUTED,
    )

    # ---------------------------------------------------------
    # 3. ANNUAL AI COST
    #
    # Cost is an economic outflow.
    # Displayed as negative/red.
    # ---------------------------------------------------------

    ai_cost_card = metric_card(
        title="Annual AI Cost",
        value=f"-${annual_ai_cost:,.0f}",
        description=(
            "API + software + oversight + maintenance "
            "+ annualized implementation"
        ),
        value_color=RED,
        indicator_color=RED,
    )

    # ---------------------------------------------------------
    # 4. ANNUAL SAVINGS
    #
    # Positive savings = green
    # Negative savings = red
    # ---------------------------------------------------------

    savings_card = metric_card(
        title="Annual Savings",
        value=money(
            annual_savings,
            show_sign=True,
        ),
        description="Labor value replaced − annual AI cost",
        value_color=sentiment_color(annual_savings),
        indicator_color=sentiment_color(annual_savings),
    )

    # ---------------------------------------------------------
    # 5. AI REPLACEMENT COST RATIO
    #
    # < 100% = AI costs less than replaced labor
    # > 100% = AI costs more than replaced labor
    # ---------------------------------------------------------

    if replacement_ratio < 100:

        ratio_color = GREEN
        ratio_description = (
            f"{100 - replacement_ratio:.1f}% below labor cost"
        )

    elif replacement_ratio > 100:

        ratio_color = RED
        ratio_description = (
            f"+{replacement_ratio - 100:.1f}% above labor cost"
        )

    else:

        ratio_color = TEXT_PRIMARY
        ratio_description = "Equal to labor cost"

    replacement_ratio_card = metric_card(
        title="AI Replacement Cost Ratio",
        value=f"{replacement_ratio:.1f}%",
        description=ratio_description,
        value_color=ratio_color,
        indicator_color=ratio_color,
    )

    # ---------------------------------------------------------
    # 6. IMPLEMENTATION PAYBACK
    # ---------------------------------------------------------

    if payback_months is not None:

        payback_value = f"{payback_months:.1f} months"
        payback_color = GREEN
        payback_description = (
            "Upfront implementation ÷ monthly recurring savings"
        )

    else:

        payback_value = "No Payback"
        payback_color = RED
        payback_description = (
            "Recurring AI cost meets or exceeds replaced labor value"
        )

    payback_card = metric_card(
        title="Implementation Payback",
        value=payback_value,
        description=payback_description,
        value_color=payback_color,
        indicator_color=payback_color,
    )

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------

    header = ft.Column(
        spacing=5,
        controls=[

            ft.Text(
                "AI Replacement Economics",
                size=25,
                weight=ft.FontWeight.BOLD,
                color=TEXT_PRIMARY,
            ),

            ft.Text(
                "Economic impact of AI substitution",
                size=13,
                color=TEXT_SECONDARY,
            ),
        ],
    )

    # ---------------------------------------------------------
    # DASHBOARD
    # ---------------------------------------------------------

    dashboard = ft.Container(
        bgcolor=BG,
        padding=24,

        border=ft.Border.all(
            width=1,
            color=BORDER,
        ),

        border_radius=18,

        content=ft.Column(
            spacing=22,
            controls=[

                # ---------------------------------------------
                # SECTION TITLE
                # ---------------------------------------------

                ft.Column(
                    spacing=3,
                    controls=[

                        ft.Text(
                            "Replacement Analysis",
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                        ),

                        ft.Text(
                            "Cost and market-value metrics",
                            size=12,
                            color=TEXT_MUTED,
                        ),
                    ],
                ),

                # ---------------------------------------------
                # DIVIDER
                # ---------------------------------------------

                ft.Container(
                    height=1,
                    bgcolor=BORDER,
                ),

                # ---------------------------------------------
                # METRIC CARDS
                # ---------------------------------------------

                ft.Row(
                    controls=[

                        market_value_card,
                        labor_replaced_card,
                        ai_cost_card,

                        savings_card,
                        replacement_ratio_card,
                        payback_card,
                    ],

                    wrap=True,
                    spacing=16,
                    run_spacing=16,
                ),
            ],
        ),
    )

    # ---------------------------------------------------------
    # ADD TO PAGE
    # ---------------------------------------------------------

    page.add(
        ft.SafeArea(
            content=EconomicsContent(
                metric_cards=(
                    market_value_card,
                    labor_replaced_card,
                    ai_cost_card,
                    savings_card,
                    replacement_ratio_card,
                    payback_card,
                ),
                spacing=25,
                controls=[
                    header,
                    dashboard,
                ],
            )
        )
    )


if __name__ == "__main__":
    ft.run(main)
