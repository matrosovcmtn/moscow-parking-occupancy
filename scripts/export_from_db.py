#!/usr/bin/env python3
"""
Export the Moscow Parking Occupancy Dataset from TimescaleDB to monthly Parquet
shards suitable for publishing on GitHub.

Outputs (under ./data/ by default):
  parking_spots.parquet
  occupancy_YYYY-MM.parquet   (one file per calendar month, UTC)

Usage:
  python scripts/export_from_db.py \
    --db-url postgresql://user:pass@host:5432/parking_db \
    --output-dir ./data \
    --since 2025-03-01 \
    --until 2026-06-01

Environment variables (overridden by CLI flags):
  DATABASE_URL    SQLAlchemy-style URL for the TimescaleDB instance.

Dependencies:
  pip install psycopg[binary] pyarrow pandas python-dateutil
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pandas as pd
import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from dateutil.relativedelta import relativedelta

LOG = logging.getLogger("export_from_db")

PARKING_SPOTS_SQL = """
SELECT
    id,
    external_id,
    name_ru,
    name_en,
    address_street_ru,
    address_street_en,
    subway_ru,
    subway_en,
    latitude::float8  AS latitude,
    longitude::float8 AS longitude,
    total_spaces,
    common_spaces,
    handicapped_spaces
FROM parking_spots
ORDER BY id
"""

OCCUPANCY_SQL = """
SELECT
    time,
    parking_id,
    free_spaces,
    free_handicapped_spaces,
    occupancy_rate
FROM parking_occupancy
WHERE time >= %(start)s AND time < %(end)s
ORDER BY time, parking_id
"""


@dataclass(frozen=True)
class MonthRange:
    start: datetime
    end: datetime

    @property
    def label(self) -> str:
        return self.start.strftime("%Y-%m")


def iter_months(since: datetime, until: datetime) -> Iterator[MonthRange]:
    """Yield MonthRange objects covering [since, until), aligned to UTC month boundaries."""
    cursor = since.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    until = until.astimezone(timezone.utc)
    while cursor < until:
        next_month = cursor + relativedelta(months=1)
        yield MonthRange(start=cursor, end=min(next_month, until))
        cursor = next_month


def export_parking_spots(conn: psycopg.Connection, output: Path) -> int:
    LOG.info("Exporting parking_spots → %s", output)
    df = pd.read_sql(PARKING_SPOTS_SQL, conn)
    df = df.astype(
        {
            "id": "int32",
            "external_id": "int32",
            "total_spaces": "Int32",
            "common_spaces": "Int32",
            "handicapped_spaces": "Int32",
        }
    )
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table,
        output,
        compression="zstd",
        compression_level=9,
    )
    LOG.info("  wrote %d rows (%.1f KB)", len(df), output.stat().st_size / 1024)
    return len(df)


def export_occupancy_month(
    conn: psycopg.Connection,
    month: MonthRange,
    output_dir: Path,
) -> tuple[Path, int]:
    output = output_dir / f"occupancy_{month.label}.parquet"
    LOG.info("Exporting occupancy %s → %s", month.label, output.name)

    df = pd.read_sql(
        OCCUPANCY_SQL,
        conn,
        params={"start": month.start, "end": month.end},
    )

    if df.empty:
        LOG.warning("  no rows for %s, skipping", month.label)
        return output, 0

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.astype(
        {
            "parking_id": "int32",
            "free_spaces": "Int32",
            "free_handicapped_spaces": "Int32",
            "occupancy_rate": "float64",
        }
    )
    # Validation: occupancy_rate is a percent 0-100 (common-spaces only),
    # see schema/occupancy.schema.json for full semantics.
    bad = df["occupancy_rate"].dropna()
    bad = bad[(bad < 0) | (bad > 100)]
    if not bad.empty:
        LOG.warning("  %d rows have out-of-range occupancy_rate in %s", len(bad), month.label)

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table,
        output,
        compression="zstd",
        compression_level=9,
        # Smaller row groups make partial reads cheaper for downstream users
        row_group_size=50_000,
    )
    size_mb = output.stat().st_size / 1024 / 1024
    LOG.info("  wrote %d rows (%.2f MB)", len(df), size_mb)
    return output, len(df)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL. Defaults to env DATABASE_URL.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data",
        help="Where to write the parquet files (default: ./data).",
    )
    p.add_argument(
        "--since",
        type=lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc),
        default=None,
        help="Lower bound (UTC, ISO date). Default: oldest record in table.",
    )
    p.add_argument(
        "--until",
        type=lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc),
        default=None,
        help="Upper bound (UTC, ISO date, exclusive). Default: now.",
    )
    p.add_argument(
        "--skip-spots",
        action="store_true",
        help="Skip exporting parking_spots.parquet.",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.db_url:
        LOG.error("--db-url not provided and DATABASE_URL env not set")
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(args.db_url) as conn:
        if not args.skip_spots:
            export_parking_spots(conn, args.output_dir / "parking_spots.parquet")

        # Auto-detect range if user didn't specify
        if args.since is None or args.until is None:
            with conn.cursor() as cur:
                cur.execute("SELECT MIN(time), MAX(time) FROM parking_occupancy")
                row = cur.fetchone()
                if not row or row[0] is None:
                    LOG.error("parking_occupancy is empty")
                    return 1
                detected_since, detected_until = row
            if args.since is None:
                args.since = detected_since
            if args.until is None:
                # +1 sec so the final partial month is included
                args.until = detected_until
        LOG.info("Date range: %s → %s", args.since.isoformat(), args.until.isoformat())

        total_rows = 0
        for month in iter_months(args.since, args.until):
            _, rows = export_occupancy_month(conn, month, args.output_dir)
            total_rows += rows

    LOG.info("Done. %d occupancy rows exported across all months.", total_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
