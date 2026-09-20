# Moscow Parking Occupancy

**4.6 million** half-hourly occupancy snapshots for **210 municipal parking lots**
in Moscow, continuous since **31 March 2025** and refreshed weekly.

Long, dense, public parking-occupancy series are rare. Most published work on
occupancy prediction still leans on the UCI *Parking Birmingham* set, which
covers October-December 2016 only. This one is longer, denser and still growing.

## Files

| File | Rows | What it is |
|---|---|---|
| `occupancy.parquet` | ~4.6 M | Snapshots every 30 minutes |
| `parking_spots.parquet` | 210 | Static metadata: coordinates, capacity, nearest metro |

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

## Read this before modelling: 39 lots are not what they look like

**19% of the Moscow lots report a constant zero free spaces.** That looks like
"completely full". It is not — the city registered these lots but does not
publish their occupancy, or the sensor died.

Measured on 2026-09-20: 39 of 210 lots reported no free space at all in the
previous 30 days; 19 of them never reported one in the entire history. One
257-space lot last showed a free space in May 2026, a 143-space lot at VDNKh
in July 2025. A 606-space lot does not stay full for five months.

They are kept in the data on purpose, but flagged:

```python
spots = pd.read_parquet("parking_spots.parquet")
live  = spots.loc[~spots.feed_silent, "id"]
occ   = occ[occ.parking_id.isin(live)]          # drops ~4.8% of rows
```

`last_free_at` lets you rebuild the flag for any as-of date instead of
trusting ours.

**Separately, the data is censored at the boundaries:** 25.2% of all rows are
exactly 100 and 7.8% exactly 0, and most of that is genuine — lots really do
fill up. Treat the target as bounded.

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

- **Municipal lots only.** Shopping malls, private lots and unpaid curbside are
  not in the Moscow public API and are not here.
- **Reported, not observed.** Values come from the upstream API; occasional
  zero-spikes and stale values are preserved rather than cleaned.
- **Gaps exist** during upstream outages.
- **No PII.** Aggregate counts only - no vehicle, plate or driver data.

## Licence

Data: **CC BY 4.0**. Original values come from Moscow Department of Transport
public parking data; this is a derivative work that aggregates and republishes
them. Please keep attribution to both.

Canonical source, full documentation and the exact export pipeline:
https://github.com/matrosovcmtn/moscow-parking-occupancy

Maintained by [ParkOut](https://parkout.ru).
