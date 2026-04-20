# Coop Panel

**Routes:** `/coop` (panel), `/coop/settings` (settings)

## Coop Panel

### Door Status
Shows current door state: **open**, **closed**, **moving**, or **stuck**.
- **Open Door** / **Close Door** buttons send manual override commands.
- A stuck-door P0 alert fires if the limit switch is not reached within 60 seconds of a command.

For the stuck door troubleshooting procedure, see [Coop Node hardware docs](../hardware/coop-node.md).

### Schedule Status
Shows today's calculated sunrise and sunset times (based on configured lat/long), plus the configured open/close offsets. Example: "Opens at 06:23 (sunrise − 15 min)".

### Egg Count Entry
Enter today's egg count in the number input and tap **Save**. The entry is stored per calendar day. Yesterday's count appears for reference.

### Production Chart
30-day chart showing actual vs. expected egg production. The expected line uses the configured flock model (breed lay rate × age factor × daylight hours).

For the production model formula, see [Flock Production Model](../configuration/automation.md#flock-production-model).

### Feed and Water
- **Feed level**: fill percentage derived from load cell weight vs. configured hopper capacity
- **Water level**: fill percentage from water level sensor
- Both show "Low" badges if below their configured thresholds

Low thresholds trigger the [`feed_low`](../configuration/alerts.md#p1-alerts-warning) and [`water_low`](../configuration/alerts.md#p1-alerts-warning) alerts respectively.

## Coop Settings

**Route:** `/coop/settings`

Configure:
- **Latitude / Longitude** — used for NOAA sunrise/sunset calculation
- **Open offset** (minutes before sunrise to open) and **Close offset** (minutes after sunset to close)
- **Hard open limit** — earliest possible open time (e.g., "06:00" — door will not open before this)
- **Hard close limit** — latest possible close time (e.g., "21:00" — door will close by this time regardless of sunset)
- **Flock configuration** — breed, hatch date, flock size, supplemental lighting on/off. See [Flock Model](../configuration/automation.md#flock-production-model).
- **Feed and water thresholds** — low-level alert trigger percentages

See [Coop Configuration](../configuration/coop.md) for all options with defaults.
