# Changelog

All notable changes to this dataset will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for the *schema* (dataset structure). Data refreshes use date-based tags.

---

## [Unreleased]

### Planned
- Weekly refresh cron via GitHub Actions
- Coverage map: per-parking record count over time
- Anomaly markers: known API outages, collector downtimes

---

## [2026-11-12] — duplicate cleanup and a seven-day gap

### Removed
- 5446 extra occupancy rows in 2422 (lot, half-hour slot) groups. The old write
  path stored a row per poll rather than per slot, so a slot could hold several
  rows: 1353 groups held byte-identical repeats, 1069 held readings taken
  minutes apart. One row per slot is kept — the last reading in the slot, which
  matches what the collector now does on conflict. A decision journal was
  written for every deleted row.

### Changed
- Eight monthly files re-exported from 2025-04 to 2026-09 as a result of the
  cleanup, plus `parking_spots.parquet` and the November file.
- Row count 5,103,138 -> 5,133,031. Lots 213, unchanged.
- Figures in README, the dataset cards and the schema recomputed against this
  release.

### Known issue
- No data between 2026-11-05 09:55 UTC and 2026-11-12 07:00 UTC. A CHECK
  constraint requiring half-hour-aligned timestamps was deployed ahead of the
  collector that produces them, every insert was rejected for seven days, and
  the collector reported success in its log the whole time. Collection resumed
  on 2026-11-12. The upstream API publishes current state only, so the week is
  not recoverable.

---

## [1.0.0] — 2026-05-29

### Added
- Initial release: 209 municipal parkings, 3,586,901 occupancy records
- Coverage: 2025-03-31 → 2026-05-28 (424 days, 30-min granularity)
- 14 monthly Parquet shards (ZSTD compressed)
- Static metadata file `parking_spots.parquet`
- JSON schemas for both tables
- Quick-start notebook, DuckDB / pandas examples
- Export script (`scripts/export_from_db.py`) for reproducibility

### Known issues
- One ~55-day gap in monitoring/backup pipeline (April 2026) — collection itself
  was fine, but pipeline metadata may show that period as low-confidence.
- Some parkings have occasional zero-spike records when the upstream API briefly
  returned stale/uninitialised values. These are preserved as-is; downstream
  users should filter if needed.
