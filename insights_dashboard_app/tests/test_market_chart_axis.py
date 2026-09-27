import importlib
import unittest


market_chart = importlib.import_module("45")


class MarketChartAxisTests(unittest.TestCase):
    def test_wage_axis_contains_every_years_median_wage(self):
        wages = [58_000, 72_000, 95_000, 131_000, 136_000]

        axis_values = market_chart.metric_axis_values(
            market_chart.METRIC_WAGE,
            wages,
        )

        self.assertLessEqual(axis_values[0], min(wages))
        self.assertGreaterEqual(axis_values[-1], max(wages))
        self.assertGreaterEqual(len(axis_values), 5)

    def test_wage_axis_expands_around_a_flat_history(self):
        wages = [75_000] * 5

        axis_values = market_chart.metric_axis_values(
            market_chart.METRIC_WAGE,
            wages,
        )

        self.assertLess(axis_values[0], wages[0])
        self.assertGreater(axis_values[-1], wages[0])
        self.assertEqual(len(axis_values), 5)


if __name__ == "__main__":
    unittest.main()
