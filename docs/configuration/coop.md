# Coop Configuration

**Route:** `/coop/settings`

## Scheduler Configuration

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `latitude` | float | Farm latitude in decimal degrees | Required |
| `longitude` | float | Farm longitude in decimal degrees | Required |
| `open_offset_min` | int | Minutes before sunrise to open door (negative = before) | -15 |
| `close_offset_min` | int | Minutes after sunset to close door | 30 |
| `hard_open_limit` | time | Earliest the door may open regardless of sunrise | "05:30" |
| `hard_close_limit` | time | Latest the door may close regardless of sunset | "21:00" |

The scheduler uses NOAA astronomical calculations (Python `astral` library) to determine local sunrise and sunset times. Times are recalculated daily.

**Example:** With `open_offset_min: -15` and sunrise at 06:38, the door opens at 06:23. With `hard_open_limit: "05:30"`, the door will never open before 05:30 even in summer when sunrise is very early.

## Flock Configuration

| Property | Type | Description |
|----------|------|-------------|
| `breed` | string | Breed name — sets the base lay rate (e.g., "Leghorn" = 0.85, "Plymouth Rock" = 0.65) |
| `hatch_date` | date | Flock hatch date — used to calculate age factor (peak at 8–18 months, declining after 24 months) |
| `flock_size` | int | Number of hens |
| `supplemental_lighting` | bool | If true, adds 14 hours of effective daylight for production model |
| `tare_weight_kg` | float | Empty feeder weight for feed level calculation |
| `hen_threshold_g` | float | Minimum expected egg weight for production model validation |
| `egg_weight_g` | float | Average egg weight for production estimation |

## Feed and Water Thresholds

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `feed_low_threshold` | float (%) | Feed fill% below which feed_low alert fires | 20.0 |
| `water_low_threshold` | float (%) | Water fill% below which water_low alert fires | 15.0 |

## Door Safety

All door commands (including the automatic schedule) require limit switch confirmation before the operation is considered complete. If the "fully open" or "fully closed" limit switch signal is not received within 60 seconds, a [`stuck_door` P0 alert](alerts.md#p0-alerts-critical) fires immediately and no further automatic commands are sent.

See [Coop Door Scheduling](automation.md#coop-door-scheduling) for the full scheduler behavior.
