import importlib
import unittest


market_chart = importlib.import_module("45")


class _CapturePage:
    def __init__(self):
        self.controls = []

    def add(self, *controls):
        self.controls.extend(controls)


def build_market_card():
    page = _CapturePage()
    market_chart.main(page)
    return page.controls[0].content


class MarketChartAxisTests(unittest.TestCase):
    def test_current_wage_is_formatted_as_us_currency(self):
        self.assertEqual(
            market_chart.format_current_value(133_080),
            "$133,080",
        )

    def test_wage_axis_contains_every_years_median_wage(self):
        wages = [58_000, 72_000, 95_000, 131_000, 136_000]

        axis_values = market_chart.wage_axis_values(wages)

        self.assertLessEqual(axis_values[0], min(wages))
        self.assertGreaterEqual(axis_values[-1], max(wages))
        self.assertGreaterEqual(len(axis_values), 5)

    def test_wage_axis_expands_around_a_flat_history(self):
        wages = [75_000] * 5

        axis_values = market_chart.wage_axis_values(wages)

        self.assertLess(axis_values[0], wages[0])
        self.assertGreater(axis_values[-1], wages[0])
        self.assertEqual(len(axis_values), 5)

    def test_wage_history_uses_exact_observations(self):
        history = [
            {"year": 2021, "median_annual_wage": 110_000},
            {"year": 2023, "median_annual_wage": 130_000},
            {"year": 2024, "median_annual_wage": 140_000},
            {"year": 2025, "median_annual_wage": 150_000},
        ]
        card = build_market_card()

        card.set_wage_history(history)

        self.assertEqual(card._wage_years, [2021, 2023, 2024, 2025])
        self.assertEqual(
            card._wage_values,
            [110_000, 130_000, 140_000, 150_000],
        )
        self.assertEqual(len(card._market_line.points), 4)
        self.assertEqual(card._target_value_text, "$150,000")

    def test_new_history_replaces_previous_occupation(self):
        card = build_market_card()
        card.set_wage_history(
            [
                {"year": 2021, "median_annual_wage": 110_000},
                {"year": 2025, "median_annual_wage": 150_000},
            ]
        )

        card.set_wage_history(
            [
                {"year": 2022, "median_annual_wage": 58_000},
                {"year": 2025, "median_annual_wage": 62_000},
            ]
        )

        self.assertEqual(card._wage_years, [2022, 2025])
        self.assertEqual(card._wage_values, [58_000, 62_000])
        self.assertEqual(len(card._market_line.points), 2)
        self.assertEqual(card._target_value_text, "$62,000")

    def test_empty_history_clears_chart_and_current_value(self):
        card = build_market_card()
        card.set_wage_history(
            [{"year": 2025, "median_annual_wage": 150_000}]
        )

        card.set_wage_history([])

        self.assertEqual(card._wage_years, [])
        self.assertEqual(card._wage_values, [])
        self.assertEqual(card._market_line.points, [])
        self.assertEqual(card._target_value_text, "—")


if __name__ == "__main__":
    unittest.main()
