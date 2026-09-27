import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import polars as pl

from occupation_service import OccupationService
from oews_service import OewsWageService, soc_code_from_onet
from onet_service import OnetService


class _JsonResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class OnetServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_returns_only_code_and_title(self):
        service = OnetService(api_key="test-key")
        service._get_json = lambda path, query: {
            "occupation": [
                {
                    "code": "15-1252.00",
                    "title": "Software Developers",
                    "href": "ignored",
                }
            ]
        }

        self.assertEqual(
            await service.search_occupations("software"),
            [
                {
                    "code": "15-1252.00",
                    "title": "Software Developers",
                }
            ],
        )

    async def test_skills_preserve_fields_and_never_exceed_six(self):
        service = OnetService(api_key="test-key")
        calls = []

        def response(path, query):
            calls.append((path, query))
            return {
                "element": [
                    {
                        "id": f"skill-{index}",
                        "name": f"Skill {index}",
                        "description": f"Description {index}",
                    }
                    for index in range(8)
                ]
            }

        service._get_json = response
        skills = await service.get_skills("15-1252.00", limit=20)

        self.assertEqual(len(skills), 6)
        self.assertEqual(
            calls,
            [
                (
                    "/online/occupations/15-1252.00/summary/skills",
                    {"start": 1, "end": 6},
                )
            ],
        )
        self.assertEqual(
            set(skills[0]),
            {"id", "name", "description"},
        )

    def test_api_key_is_sent_only_in_request_header(self):
        service = OnetService(api_key="private-key")
        response = _JsonResponse(b'{"occupation": []}')

        with patch("onet_service.urlopen", return_value=response) as mocked:
            service._get_json("/online/search", {"keyword": "nurse"})

        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "private-key")
        self.assertNotIn("private-key", request.full_url)


class OewsWageServiceTests(unittest.TestCase):
    def test_onet_extension_is_removed(self):
        self.assertEqual(soc_code_from_onet("15-1252.01"), "15-1252")

    def test_history_is_filtered_by_soc_and_sorted_by_year(self):
        with tempfile.TemporaryDirectory() as directory:
            parquet_path = Path(directory) / "wages.parquet"
            pl.DataFrame(
                {
                    "year": [2025, 2023, 2021, 2022, 2024, 2025],
                    "soc_code": [
                        "15-1252",
                        "15-1252",
                        "15-1252",
                        "15-1252",
                        "15-1252",
                        "29-1141",
                    ],
                    "occupation": ["A", "A", "A", "A", "A", "B"],
                    "median_annual_wage": [
                        150_000,
                        130_000,
                        110_000,
                        None,
                        140_000,
                        90_000,
                    ],
                },
                schema={
                    "year": pl.Int16,
                    "soc_code": pl.String,
                    "occupation": pl.String,
                    "median_annual_wage": pl.Int64,
                },
            ).write_parquet(parquet_path)

            history = OewsWageService(
                parquet_path
            ).get_wage_history("15-1252.01")

        self.assertEqual(
            history,
            [
                {"year": 2021, "median_annual_wage": 110_000},
                {"year": 2023, "median_annual_wage": 130_000},
                {"year": 2024, "median_annual_wage": 140_000},
                {"year": 2025, "median_annual_wage": 150_000},
            ],
        )

    def test_missing_soc_returns_empty_history(self):
        self.assertEqual(
            OewsWageService().get_wage_history("00-0000.00"),
            [],
        )


class _FakeOnetService:
    def __init__(self):
        self.requested_code = None

    async def get_skills(self, code, *, limit):
        self.requested_code = code
        return [
            {
                "id": "2.B.2.i",
                "name": "Complex Problem Solving",
                "description": "Description",
            }
        ]


class _FakeOewsService:
    def __init__(self):
        self.requested_code = None

    def get_wage_history(self, code):
        self.requested_code = code
        return [{"year": 2025, "median_annual_wage": 123_456}]


class OccupationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_combines_full_onet_code_skills_and_local_wages(self):
        onet = _FakeOnetService()
        oews = _FakeOewsService()
        service = OccupationService(onet, oews)

        result = await service.get_occupation(
            "15-1252.01",
            "Software Developers",
        )

        self.assertEqual(onet.requested_code, "15-1252.01")
        self.assertEqual(oews.requested_code, "15-1252.01")
        self.assertEqual(result["onet_code"], "15-1252.01")
        self.assertEqual(result["soc_code"], "15-1252")
        self.assertEqual(len(result["skills"]), 1)
        self.assertEqual(
            result["median_wages"],
            [{"year": 2025, "median_annual_wage": 123_456}],
        )


if __name__ == "__main__":
    unittest.main()
