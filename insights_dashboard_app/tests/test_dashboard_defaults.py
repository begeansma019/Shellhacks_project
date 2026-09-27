import unittest

from insights_dashboard import DEFAULT_OCCUPATIONS


class DefaultOccupationTests(unittest.TestCase):
    def test_default_occupations_match_requested_order_and_codes(self):
        self.assertEqual(
            DEFAULT_OCCUPATIONS,
            (
                {
                    "code": "15-1252.00",
                    "title": "Software Developers",
                },
                {"code": "47-2111.00", "title": "Electricians"},
                {"code": "29-1051.00", "title": "Pharmacists"},
                {"code": "41-2011.00", "title": "Cashiers"},
                {"code": "47-2031.00", "title": "Carpenters"},
                {"code": "19-2031.00", "title": "Chemists"},
                {"code": "29-1011.00", "title": "Chiropractors"},
                {
                    "code": "53-2012.00",
                    "title": "Commercial Pilots",
                },
                {
                    "code": "13-1041.00",
                    "title": "Compliance Officers",
                },
                {"code": "39-6012.00", "title": "Concierges"},
                {
                    "code": "19-1031.00",
                    "title": "Conservation Scientists",
                },
                {"code": "15-1254.00", "title": "Web Developers"},
                {
                    "code": "39-9011.00",
                    "title": "Childcare Workers",
                },
                {"code": "11-1011.00", "title": "Chief Executives"},
                {"code": "15-2011.00", "title": "Actuaries"},
            ),
        )

    def test_default_codes_are_unique(self):
        codes = [occupation["code"] for occupation in DEFAULT_OCCUPATIONS]
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
