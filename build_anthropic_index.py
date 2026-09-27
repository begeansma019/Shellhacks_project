"""
Build a compact occupation-level Anthropic Economic Index CSV.

Input:
    aei_1p_api_2026-06-26.csv

Output:
    anthropic_economic_index.csv

The input is Anthropic's June 2026 1P API Economic Index dataset.
Only GLOBAL, detailed SOC occupation rows are retained.

No third-party packages are required.
"""

from __future__ import annotations

import csv
from pathlib import Path


INPUT_FILE = Path("aei_1p_api_2026-06-26.csv")
OUTPUT_FILE = Path("anthropic_economic_index.csv")


# Metrics useful to the WorkLens Gemini risk pipeline.
METRIC_COLUMN_MAP = {
    "pct": "occupation_usage_pct",
    "collaboration_bucket_automation_pct": "automation_pct",
    "collaboration_bucket_augmentation_pct": "augmentation_pct",
    "ai_autonomy_mean": "ai_autonomy_mean",
    "human_only_time_mean": "human_only_time_hours",
    "human_with_ai_time_mean": "human_with_ai_time_minutes",
    "use_case_work_pct": "work_use_pct",
}


def parse_float(value: str | None) -> float | None:
    """Safely parse a numeric CSV value."""
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def determine_primary_mode(
    automation: float | None,
    augmentation: float | None,
) -> str:
    """
    Convert Anthropic's automation/augmentation percentages
    into a simple label for WorkLens.
    """
    if automation is None and augmentation is None:
        return "Unknown"

    if automation is None:
        return "Augmentation"

    if augmentation is None:
        return "Automation"

    if abs(automation - augmentation) < 1.0:
        return "Balanced"

    if automation > augmentation:
        return "Automation"

    return "Augmentation"


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_FILE.resolve()}\n"
            "Put this script in the same folder as "
            "aei_1p_api_2026-06-26.csv."
        )

    print(f"Reading: {INPUT_FILE}")
    print(
        "Extracting GLOBAL detailed SOC occupation data..."
    )

    # One entry per SOC code.
    #
    # The source contains multiple monthly periods. For every occupation,
    # we keep the most recent published period rather than averaging
    # different monthly snapshots together.
    occupations: dict[str, dict] = {}

    rows_read = 0
    matching_rows = 0

    with INPUT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_handle:

        reader = csv.DictReader(input_handle)

        required_columns = {
            "date_start",
            "date_end",
            "geo_id",
            "geo_level",
            "category_name",
            "hierarchy_level",
            "metric_id",
            "value",
            "node_name",
            "node_external_id",
        }

        actual_columns = set(reader.fieldnames or [])

        missing_columns = required_columns - actual_columns

        if missing_columns:
            raise ValueError(
                "Input CSV is missing expected columns: "
                + ", ".join(sorted(missing_columns))
            )

        for row in reader:
            rows_read += 1

            # Anthropic's 1P API file is global, but explicitly
            # enforce GLOBAL/global so the script stays safe if
            # the source format changes later.
            if row["geo_id"].strip().upper() != "GLOBAL":
                continue

            if row["geo_level"].strip().lower() != "global":
                continue

            # We only want occupation records.
            if row["category_name"].strip() != "soc_occupation":
                continue

            # Level 0 = detailed SOC occupation.
            try:
                hierarchy_level = int(
                    row["hierarchy_level"]
                )
            except (TypeError, ValueError):
                continue

            if hierarchy_level != 0:
                continue

            metric_id = row["metric_id"].strip()

            if metric_id not in METRIC_COLUMN_MAP:
                continue

            soc_code = row["node_external_id"].strip()
            title = row["node_name"].strip()
            date_start = row["date_start"].strip()
            date_end = row["date_end"].strip()

            if not soc_code or not title:
                continue

            value = parse_float(row["value"])

            if value is None:
                continue

            matching_rows += 1

            existing = occupations.get(soc_code)

            # If this is the first row for the occupation, or it
            # belongs to a newer publication period, create/reset
            # the occupation record.
            if (
                existing is None
                or date_end > existing["date_end"]
            ):
                existing = {
                    "soc_code": soc_code,
                    "title": title,
                    "date_start": date_start,
                    "date_end": date_end,
                }

                occupations[soc_code] = existing

            # Ignore rows from older monthly periods.
            if date_end != existing["date_end"]:
                continue

            output_column = METRIC_COLUMN_MAP[metric_id]
            existing[output_column] = value

    # ---------------------------------------------------------
    # Calculate derived fields
    # ---------------------------------------------------------

    output_rows = []

    for soc_code, occupation in occupations.items():

        automation = occupation.get("automation_pct")
        augmentation = occupation.get("augmentation_pct")

        occupation["primary_mode"] = determine_primary_mode(
            automation,
            augmentation,
        )

        occupation["source"] = (
            "Anthropic Economic Index 1P API 2026-06-26"
        )

        output_rows.append(occupation)

    # Sort by SOC code for predictable diffs / Git history.
    output_rows.sort(
        key=lambda row: row["soc_code"]
    )

    fieldnames = [
        "soc_code",
        "title",
        "date_start",
        "date_end",
        "occupation_usage_pct",
        "automation_pct",
        "augmentation_pct",
        "primary_mode",
        "ai_autonomy_mean",
        "human_only_time_hours",
        "human_with_ai_time_minutes",
        "work_use_pct",
        "source",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output_handle:

        writer = csv.DictWriter(
            output_handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in output_rows:
            writer.writerow(row)

    size_kb = OUTPUT_FILE.stat().st_size / 1024

    print()
    print("Done.")
    print(f"Rows scanned: {rows_read:,}")
    print(f"Relevant metric rows: {matching_rows:,}")
    print(f"Detailed occupations: {len(output_rows):,}")
    print(f"Output: {OUTPUT_FILE.resolve()}")
    print(f"Output size: {size_kb:,.1f} KB")

    # Helpful validation for the dashboard's default occupation.
    software = [
        row
        for row in output_rows
        if row["soc_code"] == "15-1252"
    ]

    if software:
        print()
        print("Software Developers sample:")
        for key, value in software[0].items():
            print(f"  {key}: {value}")
    else:
        print()
        print(
            "Note: SOC 15-1252 was not present in the "
            "published detailed-occupation subset."
        )


if __name__ == "__main__":
    main()