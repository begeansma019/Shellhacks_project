from pathlib import Path

import polars as pl


DEFAULT_PARQUET_PATH = (
    Path(__file__).resolve().parent.parent
    / "oews_median_wages_2021_2025.parquet"
)


class OewsDataError(RuntimeError):
    """The local OEWS wage data could not be queried."""


def soc_code_from_onet(onet_code: str) -> str:
    code = onet_code.strip()
    if not code:
        raise ValueError("An O*NET-SOC code is required.")
    return code.split(".", maxsplit=1)[0]


class OewsWageService:
    def __init__(self, parquet_path: str | Path = DEFAULT_PARQUET_PATH):
        self._parquet_path = Path(parquet_path).resolve()

    def get_wage_history(self, onet_code: str) -> list[dict[str, int]]:
        soc_code = soc_code_from_onet(onet_code)

        try:
            rows = (
                pl.scan_parquet(self._parquet_path)
                .filter(
                    (pl.col("soc_code") == soc_code)
                    & pl.col("year").is_between(2021, 2025)
                    & pl.col("median_annual_wage").is_not_null()
                )
                .select("year", "median_annual_wage")
                .sort("year")
                .collect()
                .to_dicts()
            )
        except (FileNotFoundError, OSError, pl.exceptions.PolarsError) as error:
            raise OewsDataError(
                "The local OEWS wage history could not be read."
            ) from error

        return [
            {
                "year": int(row["year"]),
                "median_annual_wage": int(
                    row["median_annual_wage"]
                ),
            }
            for row in rows
        ]
