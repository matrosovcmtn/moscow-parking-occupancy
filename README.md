# Moscow Parking Occupancy Dataset

> Open dataset of 30-minute parking occupancy snapshots for 209 municipal parking lots in Moscow, Russia.
> Полностью открытый датасет занятости 209 муниципальных парковок Москвы с шагом 30 минут.

[![License: CC BY 4.0](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-lightgrey.svg)](./DATA_LICENSE)
[![License: MIT](https://img.shields.io/badge/Code%20License-MIT-yellow.svg)](./LICENSE)

---

## TL;DR

- **3.58 million** occupancy records
- **209 parking lots** with 28,115 total spaces
- **30-minute granularity**, continuous from **2025-03-31** onwards
- **Parquet** format, sharded by month (~3–5 MB / file)
- Source: Moscow Department of Transport public parking data
- Maintained by [ParkOut](https://parkout.ru) — updated weekly

---

## Contents

| File | Description | Rows | Size |
|---|---|---|---|
| `data/parking_spots.parquet` | Static metadata: name, address, coordinates, capacity per parking | 209 | ~10 KB |
| `data/occupancy_YYYY-MM.parquet` | Time-series occupancy snapshots, one file per month | ~256 k | ~3–5 MB |
| `schema/parking_spots.schema.json` | JSON Schema for parking_spots | — | — |
| `schema/occupancy.schema.json` | JSON Schema for occupancy | — | — |
| `scripts/export_from_db.py` | The exact pipeline used to produce these files | — | — |
| `scripts/refresh.sh` | Server-side cron wrapper: export → commit → push | — | — |
| `examples/load_pandas.py` | Minimal example: load one month into pandas | — | — |
| `examples/load_duckdb.py` | Query all months as a single table via DuckDB | — | — |

Notebooks with deeper analysis (typical-patterns heatmap, ML baseline) are
planned for v1.1 — see [`CHANGELOG.md`](./CHANGELOG.md).

---

## Schema

### `parking_spots`

| Column | Type | Description |
|---|---|---|
| `id` | int32 | Internal stable id |
| `external_id` | int32 | Original id from the upstream Moscow source |
| `name_ru` | string | Russian name |
| `name_en` | string | English name |
| `address_street_ru` | string | Street address (RU) |
| `address_street_en` | string | Street address (EN) |
| `subway_ru` | string | Nearest metro station (RU) |
| `subway_en` | string | Nearest metro station (EN) |
| `latitude` | float64 | WGS-84 latitude |
| `longitude` | float64 | WGS-84 longitude |
| `total_spaces` | int32 | Total capacity |
| `common_spaces` | int32 | Standard spaces |
| `handicapped_spaces` | int32 | Accessible spaces |

### `parking_occupancy`

| Column | Type | Description |
|---|---|---|
| `time` | timestamp\[ns, UTC\] | Snapshot timestamp (UTC) |
| `parking_id` | int32 | Foreign key → `parking_spots.id` |
| `free_spaces` | int32 | Total number of free spaces at this moment (common + handicapped) |
| `free_handicapped_spaces` | int32 | Free accessible (handicapped) spaces |
| `occupancy_rate` | float64 | Percent **0–100** of *common* spaces occupied. See note below. |

> **Important — `occupancy_rate` semantics.** The collector computes this as
> `(common_total - common_free) / common_total * 100` using the **declared
> `common_spaces` capacity only** (i.e. excluding handicapped spots). It is
> *not* the same as `1 - free_spaces / total_spaces`, which would mix common
> and handicapped spaces together. If you want the all-inclusive ratio,
> compute it yourself:
>
> ```python
> df["overall_occupancy"] = 1 - df["free_spaces"] / spots["total_spaces"]
> ```

Primary key: `(time, parking_id)`. Source poll interval: 30 minutes ± 1 min jitter.

---

## Quick start

```python
import pandas as pd

spots = pd.read_parquet("data/parking_spots.parquet")
may = pd.read_parquet("data/occupancy_2026-05.parquet")

print(spots.head())
print(may.head())

# Join to enrich occupancy with parking name
df = may.merge(spots[["id", "name_ru", "latitude", "longitude"]],
               left_on="parking_id", right_on="id", how="left")
```

Or query everything at once with DuckDB:

```python
import duckdb
con = duckdb.connect()
df = con.execute("""
    SELECT s.name_ru, o.time, o.occupancy_rate
    FROM   'data/occupancy_*.parquet' o
    JOIN   'data/parking_spots.parquet' s ON s.id = o.parking_id
    WHERE  o.time >= TIMESTAMP '2026-05-01'
    ORDER  BY o.time DESC
    LIMIT  20
""").df()
```

---

## Updates

This dataset is refreshed **every Monday at 04:00 UTC**. The most recent month file is
always partial and overwritten on each refresh; older months are append-only.

See [`CHANGELOG.md`](./CHANGELOG.md) for the history of releases.

---

## Limitations & caveats

- **Only municipal parkings.** Shopping malls, private lots, and curbside non-paid
  spaces are not part of the Moscow public API and are not in this dataset.
- **Occupancy is the API's reported value**, not directly observed. Occasional
  zero-spike or stale-value artefacts exist; we do not clean them — raw data preserved.
- **No predictions.** This is observational data only. The ML predictions used by
  parkout.ru live in a separate component and are not redistributed.
- **No PII.** Parking lots are aggregate counts; no individual vehicle, plate, or
  driver information is collected or shared.
- **Gaps may exist** during source-API outages or our collector downtime
  (April 2026 had a 55-day backup gap — collection itself was fine).

---

## How this dataset was produced

```
Moscow Department of Transport public parking data
        │ (polled every 30 min)
        ▼
parking-data-collector  (FastAPI + APScheduler, Python)
        │ bulk insert
        ▼
TimescaleDB hypertable  parking_occupancy (chunks per ~7 days)
        │ pg_dump-style export, monthly partitioning
        ▼
data/occupancy_YYYY-MM.parquet
```

The export script `scripts/export_from_db.py` is included so the pipeline is
fully reproducible. The companion `parking-data-collector` service is open-sourced
separately (see *Related repositories* below).

---

## Citation

If you use this dataset in academic work, please cite:

```
Matrosov, D. (2026). Moscow Parking Occupancy Dataset. GitHub.
https://github.com/matrosovcmtn/moscow-parking-occupancy
```

BibTeX:

```bibtex
@misc{matrosov2026moscowparking,
  author       = {Matrosov, Danil},
  title        = {Moscow Parking Occupancy Dataset},
  year         = {2026},
  publisher    = {GitHub},
  howpublished = {\url{https://github.com/matrosovcmtn/moscow-parking-occupancy}}
}
```

---

## Licensing

- **Code** in this repository (export scripts, notebooks, examples) — [MIT](./LICENSE).
- **Data files** (`data/*.parquet`) — [Creative Commons Attribution 4.0](./DATA_LICENSE).
- **Source attribution:** the original occupancy values are obtained from public
  Moscow Department of Transport parking data. This dataset is a derivative work
  that aggregates, normalises, and republishes those values. Users redistributing
  this data must keep attribution to both this dataset and the original Moscow
  source. See [`DATA_LICENSE`](./DATA_LICENSE) for full text.

If your use case is commercial and you need stronger licensing guarantees about
the original source, you should independently verify the upstream terms of
service before redistribution.

---

## Related repositories

- [`parking-data-collector`](#) — the FastAPI collector service that polls the
  Moscow API and writes to TimescaleDB. *(repo link added once published.)*
- [`parking-ml`](https://github.com/matrosovcmtn/parking-ml) — the ML service
  that runs occupancy predictions on top of this data. Used by parkout.ru.

---

## Contributing

Issues and PRs welcome:

- Found a bug in the exported data? Open an issue with the affected file and rows.
- Want to add a notebook (visualisation, benchmark, model)? PR to `notebooks/`.
- Want to add bindings (R, Julia)? PR to `examples/`.

For larger contributions (extra cities, new schemas) please open an issue first.

---

## Acknowledgements

- Government of Moscow Department of Transport — for providing the public parking
  occupancy API that makes this dataset possible.
- TimescaleDB — for handling 3.5 M+ rows at insert-time efficiently.
- The Parquet/Arrow ecosystem — for making 408 MB of data fit in a 50 MB GitHub repo.
