# Zones Screen

**Routes:** `/zones` (list), `/zones/[zone-id]` (detail)

## Zones List

Shows all configured zones as cards. Each card shows composite health score, current VWC, and a sparkline of recent moisture trend.

## Zone Detail

Tap a zone card to open its detail view. The detail screen shows:

### Sensor Readings Section
- Live VWC %, pH, and temperature with quality badges and freshness timestamps
- If quality flag is SUSPECT or BAD, a diagnostic hint explains why (e.g., "Reading unchanged for 30+ samples")

**Quality flags:**

| Flag | Meaning |
|------|---------|
| GOOD | Reading within expected range, recently updated |
| SUSPECT | Reading may be unreliable — check sensor calibration or connection |
| BAD | Reading is clearly invalid or sensor hardware error detected |
| STALE | No new reading received in >5 minutes |

### 7-Day and 30-Day History Charts
Interactive line charts showing moisture, pH, and temperature trends. Use the time range toggle to switch between 7-day and 30-day views.

### Irrigation Section
- **Current status**: open / closed / unknown
- **Open Valve** button — sends an open command to the edge node relay. Disabled if another zone is already irrigating (single-zone invariant).
- **Close Valve** button — sends a close command.
- Command status updates within 5 seconds as the hub receives the actuator acknowledgement.

For full irrigation automation behavior, see [Irrigation Automation](../configuration/automation.md#irrigation-automation).

### Calibration Section
Shows pH calibration status for this zone:
- Last calibration date
- Due date (2-week cadence)
- If overdue: a "Record Calibration" button appears. See [pH Calibration Settings](settings.md#calibration).

## Zone Configuration
See [Zone Configuration](../configuration/zones.md) for all configurable options.
