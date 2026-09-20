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
- `free_spaces` - free spaces (common + accessible)
- `free_handicapped_spaces` - free accessible spaces
- `occupancy_rate` - percent 0-100 of **common** spaces occupied

> `occupancy_rate` is `(common_total - common_free) / common_total * 100` over
> declared **common** capacity only. It is *not* `1 - free_spaces / total_spaces`,
> which would mix common and accessible spaces.

**parking_spots** - `id`, `external_id`, `name_ru`, `name_en`,
`address_street_ru`, `address_street_en`, `subway_ru`, `subway_en`,
`latitude`, `longitude`, `total_spaces`, `common_spaces`, `handicapped_spaces`.

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
