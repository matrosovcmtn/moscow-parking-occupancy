# Moscow Parking Occupancy

**5.17 million** half-hourly occupancy snapshots for **213 municipal parking lots**
in Moscow, continuous since **31 March 2025** and refreshed weekly.

Long, dense, public parking-occupancy series are rare. Most published work on
occupancy prediction still leans on the UCI *Parking Birmingham* set, which
covers October-December 2016 only. This one is longer, denser and still growing.

## Files

| File | Rows | What it is |
|---|---|---|
| `occupancy.parquet` | ~5.10 M | Snapshots every 30 minutes |
| `parking_spots.parquet` | 213 | Static metadata: coordinates, capacity, nearest metro |

## Schema

**occupancy** - primary key `(time, parking_id)`

- `time` - snapshot timestamp, UTC
- `parking_id` - foreign key to `parking_spots.id`
- `free_spaces` - free spaces in the **common** (non-accessible) pool
- `free_handicapped_spaces` - free accessible spaces
- `occupancy_rate` - percent of **common** spaces occupied, normally 0-100

> `occupancy_rate` is `(common_total - common_free) / common_total * 100` over
> declared **common** capacity only, using the capacity in force at the time of
> the snapshot. It is *not* `1 - free_spaces / total_spaces`, which would mix
> common and accessible spaces. See *Known quirks* below before treating any of
> these three columns as bounded.

**parking_spots** - `id`, `external_id`, `name_ru`, `name_en`,
`address_street_ru`, `address_street_en`, `subway_ru`, `subway_en`,
`latitude`, `longitude`, `total_spaces`, `common_spaces`, `handicapped_spaces`,
plus `last_free_at` and `feed_silent` (see the warning below).

## Read this before modelling: 48 lots are not what they look like

**23% of the Moscow lots report a constant zero free spaces.** That looks like
"completely full". It is not — the city registered these lots but does not
publish their occupancy, or the sensor died.

Measured on 2026-11-19: 48 of 213 lots reported no free space at all in the
previous 30 days; 21 of them never reported one in the entire history. A
606-space lot last showed a free space in April 2026, a 288-space lot never
has, a 257-space lot near Sportivnaya in May 2026. A 606-space lot does not
stay full for seven months.

They are kept in the data on purpose, but flagged:

```python
spots = pd.read_parquet("parking_spots.parquet")
live  = spots.loc[~spots.feed_silent, "id"]
occ   = occ[occ.parking_id.isin(live)]          # drops 17.0% of rows
```

`last_free_at` lets you rebuild the flag for any as-of date instead of
trusting ours.

**Separately, the data is censored at the boundaries:** 25.8% of all rows are
exactly 100 and 7.4% exactly 0, and most of that is genuine — lots really do
fill up. Treat the target as bounded.

## Known quirks in the numbers themselves

Measured on the current release (5,168,635 rows). Nothing here is cleaned - this
is an observational archive - but none of it should surprise you.

**1. `occupancy_rate` goes below zero in 19,785 rows (0.38%),** down to -1000.
All of them sit in 27 lots between 18 May and 9 December 2025. Before January
2026 the collector computed the percentage without clamping the free-space count
to the declared capacity, so a lot reporting more free spaces than it officially
has produced a negative percentage. The clamp landed in January 2026 and no later
row is affected. `free_spaces` is untouched, so nothing is lost:

```python
occ = occ[occ.occupancy_rate >= 0]           # drops 0.38% of rows
```

**2. You cannot recompute `occupancy_rate` from `parking_spots`.** Its
denominator is the capacity declared *at the moment of the snapshot*, while
`parking_spots.common_spaces` carries only today's value. 77 of the 192 lots that
ever report a partial occupancy re-declared capacity at least once over the 21
months. Recover the denominator from the row itself instead:

```python
# exact for every row with 0 < occupancy_rate < 100
declared = free_spaces / (1 - occupancy_rate / 100)
```

**3. The accessible-space counter emits garbage.** `free_handicapped_spaces`
exceeds the declared accessible capacity in 131,639 rows (2.5%, 38 lots) and peaks
at 9,979 free accessible spaces in a lot that declares 2. `free_spaces` exceeds
the declared common capacity in 166,936 rows (3.2%, 58 lots), and is *smaller*
than `free_handicapped_spaces` in 6.7% of rows - the two are independent upstream
counters, not a total and one of its parts. Neither is bounded by the capacity
columns.

## Caveats

- **Municipal lots only.** Shopping malls, private lots and unpaid curbside are
  not in the Moscow public API and are not here.
- **Reported, not observed.** Values come from the upstream API; occasional
  zero-spikes and stale values are preserved rather than cleaned.
- **Gaps exist** during upstream outages. The largest single gap is 2026-11-05
  to 2026-11-12: a database constraint requiring half-hour-aligned timestamps
  was deployed ahead of the collector that produces them, every write was
  rejected for seven days, and the collector logged success throughout. The
  source publishes current state only, so the week cannot be recovered.
- **One row per lot per half-hour slot.** Until 2026-11-12 the history also
  held 5446 extra rows in 2422 slots, left by a write path that did not resolve
  conflicts; 1353 of those slots held identical repeats and 1069 held readings
  taken minutes apart. They were removed and the last reading in each slot was
  kept, which is what the collector now does on conflict. Eight monthly files
  from 2025-04 to 2026-09 changed as a result.
- **No PII.** Aggregate counts only - no vehicle, plate or driver data.

## Licence

Data: **CC BY 4.0**. Original values come from Moscow Department of Transport
public parking data; this is a derivative work that aggregates and republishes
them. Please keep attribution to both.

Archived on Zenodo with a DOI, which is the form to cite in a paper:
https://doi.org/10.5281/zenodo.24405339 (that link follows the newest
version; the snapshot of 20 November 2026 is 10.5281/zenodo.24405340).

Canonical source, full documentation and the exact export pipeline:
https://github.com/matrosovcmtn/moscow-parking-occupancy

Maintained by [ParkOut](https://parkout.ru).
