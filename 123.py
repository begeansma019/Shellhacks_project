# build_oews_wages.py

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

import polars as pl
import requests


YEARS = range(2021, 2026)

OUTPUT_FILE = Path("oews_median_wages_2021_2025.parquet")

BLS_URL_TEMPLATE = (
    "https://www.bls.gov/oes/special-requests/oesm{yy}nat.zip"
)


def download_bls_zip(year: int) -> bytes:
    """
    Download the national OEWS ZIP file for a given year.
    Example:
        2025 -> oesm25nat.zip
    """
    yy = str(year)[-2:]
    url = BLS_URL_TEMPLATE.format(yy=yy)

    print(f"Downloading {year}: {url}")

    response = requests.get(
        url,
        timeout=60,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "OEWS wage data research / educational project"
            )
        },
    )

    response.raise_for_status()
    return response.content


def find_national_xlsx(zip_bytes: bytes) -> tuple[zipfile.ZipFile, str]:
    """
    Find the national_MYYYY_dl.xlsx file inside the BLS ZIP.
    """
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))

    xlsx_files = [
        name
        for name in zf.namelist()
        if name.lower().endswith(".xlsx")
    ]

    if not xlsx_files:
        raise RuntimeError("No XLSX file found inside BLS ZIP.")

    # Prefer BLS's national_MYYYY_dl.xlsx file.
    national_files = [
        name
        for name in xlsx_files
        if Path(name).name.lower().startswith("national_")
    ]

    filename = national_files[0] if national_files else xlsx_files[0]

    return zf, filename


def clean_wage_column(column: str) -> pl.Expr:
    """
    Convert OEWS wage values into nullable integers.

    Values that BLS suppresses or publishes as special symbols
    become null instead of causing the pipeline to fail.
    """
    return (
        pl.col(column)
        .cast(pl.String)
        .str.replace_all(r"[$,]", "")
        .cast(pl.Float64, strict=False)
        .round(0)
        .cast(pl.Int64)
    )


def load_year(year: int) -> pl.DataFrame:
    zip_bytes = download_bls_zip(year)
    zf, xlsx_name = find_national_xlsx(zip_bytes)

    print(f"  Reading {xlsx_name}")

    with tempfile.TemporaryDirectory() as temp_dir:
        xlsx_path = Path(temp_dir) / Path(xlsx_name).name

        with zf.open(xlsx_name) as src:
            xlsx_path.write_bytes(src.read())

        df = pl.read_excel(
            xlsx_path,
            engine="calamine",
        )

    # Normalize BLS column names.
    df = df.rename(
        {
            column: column.strip().upper()
            for column in df.columns
        }
    )

    required_columns = {
        "OCC_CODE",
        "OCC_TITLE",
        "O_GROUP",
        "A_MEDIAN",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise RuntimeError(
            f"{year}: missing expected BLS columns: {sorted(missing)}"
        )

    # Only keep individual occupations.
    # This removes broad rows such as:
    #   15-0000 Computer and Mathematical Occupations
    #   00-0000 All Occupations
    df = (
        df
        .filter(
            pl.col("O_GROUP")
            .cast(pl.String)
            .str.to_lowercase()
            == "detailed"
        )
        .select(
            pl.lit(year).cast(pl.Int16).alias("year"),

            pl.col("OCC_CODE")
            .cast(pl.String)
            .str.strip_chars()
            .alias("soc_code"),

            pl.col("OCC_TITLE")
            .cast(pl.String)
            .str.strip_chars()
            .alias("occupation"),

            clean_wage_column("A_MEDIAN")
            .alias("median_annual_wage"),
        )
    )

    print(
        f"  {year}: {df.height:,} detailed occupations "
        f"({df['median_annual_wage'].null_count():,} missing/suppressed wages)"
    )

    return df


def main() -> None:
    frames = []

    for year in YEARS:
        frames.append(load_year(year))

    wages = (
        pl.concat(
            frames,
            how="diagonal_relaxed",
        )
        .unique(
            subset=["year", "soc_code"],
            keep="first",
        )
        .sort(
            ["soc_code", "year"]
        )
    )

    # Sanity checks
    if wages.is_empty():
        raise RuntimeError("Final dataset is empty.")

    duplicate_count = (
        wages
        .group_by(["year", "soc_code"])
        .len()
        .filter(pl.col("len") > 1)
        .height
    )

    if duplicate_count:
        raise RuntimeError(
            f"Found {duplicate_count} duplicated SOC/year combinations."
        )

    wages.write_parquet(
        OUTPUT_FILE,
        compression="zstd",
        statistics=True,
    )

    print()
    print("Finished.")
    print(f"Rows: {wages.height:,}")
    print(f"Output: {OUTPUT_FILE.resolve()}")
    print()
    print(wages.head(10))


if __name__ == "__main__":
    main()