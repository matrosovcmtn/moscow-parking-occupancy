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
