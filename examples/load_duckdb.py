"""
Query the entire dataset as a single virtual table using DuckDB.

DuckDB reads Parquet files directly without loading them all into memory,
so you can write SQL against ~3.5M rows on a laptop without preprocessing.

Run from the repo root:
    pip install duckdb
    python examples/load_duckdb.py
"""

from pathlib import Path

import duckdb

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    con = duckdb.connect()

    # Average occupancy by day-of-week + hour, across all months,
    # weighted by number of spaces per parking.
    query = f"""
        WITH joined AS (
            SELECT
                o.time,
                o.occupancy_rate,
                s.total_spaces
            FROM read_parquet('{DATA_DIR}/occupancy_*.parquet') o
            JOIN read_parquet('{DATA_DIR}/parking_spots.parquet') s
              ON s.id = o.parking_id
            WHERE o.occupancy_rate IS NOT NULL
              AND s.total_spaces > 0
        )
        SELECT
            dayofweek(time AT TIME ZONE 'Europe/Moscow') AS dow_msk,
            hour(time AT TIME ZONE 'Europe/Moscow')     AS hour_msk,
            SUM(occupancy_rate * total_spaces) / SUM(total_spaces) AS avg_occupancy,
            COUNT(*) AS n
        FROM joined
        GROUP BY dow_msk, hour_msk
        ORDER BY dow_msk, hour_msk
    """

    df = con.execute(query).df()
    print("Average occupancy by day-of-week × hour (Moscow time):")
    print(df.head(24))
    print(f"\nTotal cells: {len(df)} (expected 7×24 = 168)")


if __name__ == "__main__":
    main()
