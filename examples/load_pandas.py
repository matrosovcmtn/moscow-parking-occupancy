"""
Minimal example: load one month of occupancy data + metadata, join, plot.

Run from the repo root:
    pip install pandas pyarrow matplotlib
    python examples/load_pandas.py
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MONTH = "2026-05"


def main() -> None:
    spots = pd.read_parquet(DATA_DIR / "parking_spots.parquet")
    occ = pd.read_parquet(DATA_DIR / f"occupancy_{MONTH}.parquet")

    print(f"Parkings: {len(spots)}")
    print(f"Occupancy rows for {MONTH}: {len(occ):,}")
    print()

    df = occ.merge(
        spots[["id", "name_ru", "total_spaces"]],
        left_on="parking_id",
        right_on="id",
        how="left",
    ).drop(columns=["id"])

    # Average common-spaces occupancy per parking over the month (0-100%)
    avg = (
        df.groupby(["parking_id", "name_ru", "total_spaces"], dropna=False)["occupancy_rate"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
    )
    print(f"Top 10 most-occupied parkings in {MONTH} (avg common occupancy %)")
    print(avg.to_string())


if __name__ == "__main__":
    main()
