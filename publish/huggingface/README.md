---
license: cc-by-4.0
language:
  - en
  - ru
task_categories:
  - time-series-forecasting
  - tabular-regression
tags:
  - parking
  - smart-city
  - urban-mobility
  - moscow
  - occupancy
  - open-data
size_categories:
  - 1M<n<10M
configs:
  - config_name: occupancy
    data_files: data/occupancy_*.parquet
  - config_name: parking_spots
    data_files: data/parking_spots.parquet
---

# Moscow Parking Occupancy Dataset

4.6 million half-hourly occupancy snapshots for **210 municipal parking lots**
in Moscow, continuous since **31 March 2025** and refreshed every Monday.

Long, dense, public occupancy series are rare: most published work on parking
occupancy prediction still leans on the UCI *Parking Birmingham* set, which
covers October–December 2016 only.

## Configs

| Config | Rows | What it is |
|---|---|---|
| `occupancy` | ~4.6 M | Snapshots every 30 minutes |
| `parking_spots` | 210 | Static metadata: coordinates, capacity, nearest metro |

```python
from datasets import load_dataset

occ = load_dataset("matrosovcmtn/moscow-parking-occupancy", "occupancy", split="train")
spots = load_dataset("matrosovcmtn/moscow-parking-occupancy", "parking_spots", split="train")
```

## Schema

**`occupancy`** — primary key `(time, parking_id)`

| Column | Type | Description |
|---|---|---|
| `time` | timestamp[ns, UTC] | Snapshot timestamp |
| `parking_id` | int32 | Foreign key to `parking_spots.id` |
| `free_spaces` | int32 | Free spaces in the **common** (non-accessible) pool |
| `free_handicapped_spaces` | int32 | Free accessible spaces. Least reliable column — see quirks |
| `occupancy_rate` | float64 | Percent of **common** spaces occupied, normally 0–100 |

> `occupancy_rate` is computed as `(common_total - common_free) / common_total * 100`
> over declared **common** capacity only, using the capacity in force at the time
> of the snapshot — it is *not* `1 - free_spaces / total_spaces`. See *Known quirks*
> below before treating any of these three columns as bounded.

**`parking_spots`** — `id`, `external_id`, `name_ru`, `name_en`,
`address_street_ru`, `address_street_en`, `subway_ru`, `subway_en`,
`latitude`, `longitude`, `total_spaces`, `common_spaces`, `handicapped_spaces`,
`last_free_at`, `feed_silent`.

## Read this before modelling: 39 lots are not what they look like

**19% of the Moscow lots report a constant zero free spaces.** That looks like
"completely full". It is not — the city registered these lots but does not
publish their occupancy, or the sensor died.

Measured on 2026-09-20: 39 of 210 lots reported no free space at all in the
previous 30 days; 19 never reported one in the entire history. One 257-space
lot last showed a free space in May 2026, a 143-space lot at VDNKh in July
2025. A 606-space lot does not stay full for five months.

Kept in the data on purpose, but flagged:

```python
spots = spots.to_pandas()
live = set(spots.loc[~spots.feed_silent, "id"])
occ = occ.filter(lambda r: r["parking_id"] in live)   # drops ~4.8% of rows
```

`last_free_at` lets you rebuild the flag for any as-of date instead of
trusting ours.

**Separately, the data is censored at the boundaries:** 25.2% of all rows are
exactly 100 and 7.8% exactly 0 — mostly genuine, lots really do fill up.
Treat the target as bounded.

## Known quirks in the numbers themselves

Measured on the current release (4,684,084 rows). Nothing here is cleaned - this
is an observational archive - but none of it should surprise you.

**1. `occupancy_rate` goes below zero in 19,792 rows (0.42%),** down to -1000.
All of them sit in 27 lots between 18 May and 9 December 2025. Before January
2026 the collector computed the percentage without clamping the free-space count
to the declared capacity, so a lot reporting more free spaces than it officially
has produced a negative percentage. The clamp landed in January 2026 and no later
row is affected. `free_spaces` is untouched, so nothing is lost:

```python
occ = occ[occ.occupancy_rate >= 0]           # drops 0.42% of rows
```

**2. You cannot recompute `occupancy_rate` from `parking_spots`.** Its
denominator is the capacity declared *at the moment of the snapshot*, while
`parking_spots.common_spaces` carries only today's value. 74 of the 190 lots that
ever report a partial occupancy re-declared capacity at least once over the 19
months. Recover the denominator from the row itself instead:

```python
# exact for every row with 0 < occupancy_rate < 100
declared = free_spaces / (1 - occupancy_rate / 100)
```

**3. The accessible-space counter emits garbage.** `free_handicapped_spaces`
exceeds the declared accessible capacity in 94,435 rows (2.0%, 36 lots) and peaks
at 9,979 free accessible spaces in a lot that declares 2. `free_spaces` exceeds
the declared common capacity in 116,327 rows (2.5%, 55 lots), and is *smaller*
than `free_handicapped_spaces` in 6.8% of rows - the two are independent upstream
counters, not a total and one of its parts. Neither is bounded by the capacity
columns.

## Caveats

- **Municipal lots only.** Malls, private lots and unpaid curbside are not in
  the Moscow public API and are not here.
- **Reported, not observed.** Values come from the upstream API; occasional
  zero-spikes and stale values are preserved rather than cleaned.
- **Gaps exist** during upstream outages.
- **No PII.** Aggregate counts only — no vehicle, plate or driver data.

## Licence and citation

Data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Original values
come from Moscow Department of Transport public parking data; this is a
derivative work that aggregates and republishes them. Keep attribution to both.

```bibtex
@misc{matrosov2026moscowparking,
  author       = {Matrosov, Danil},
  title        = {Moscow Parking Occupancy Dataset},
  year         = {2026},
  howpublished = {\url{https://github.com/matrosovcmtn/moscow-parking-occupancy}}
}
```

Canonical source and full documentation:
[github.com/matrosovcmtn/moscow-parking-occupancy](https://github.com/matrosovcmtn/moscow-parking-occupancy)
· Maintained by [ParkOut](https://parkout.ru)
