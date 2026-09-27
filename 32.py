import polars as pl

onet_code = "15-1252.00"

soc_code = onet_code.split(".")[0]

result = (
    pl.scan_parquet("oews_median_wages_2021_2025.parquet")
    .filter(pl.col("soc_code") == soc_code)
    .sort("year")
    .collect()
)

print(result)