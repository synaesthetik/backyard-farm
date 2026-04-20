# Automation Rules

The platform automates two core workflows: irrigation and coop door scheduling. Both follow a **recommend-and-confirm** pattern — the system generates recommendations but requires farmer approval before acting.

## Irrigation Automation

### Threshold-Based Recommendations
The bridge monitors VWC readings for each zone every 15 minutes. When a zone's VWC falls below its configured `vwc_low` threshold:
1. A recommendation is generated and placed in the queue
2. If a recommendation of the same type already exists for that zone, it is suppressed (deduplication)
3. After a zone is irrigated, a **cool-down window** (default: 2 hours) suppresses new recommendations (prevents re-triggering on lag sensor readings)

### Sensor-Feedback Irrigation Loop
After a farmer approves an irrigation recommendation:
1. Hub sends "open valve" command to the zone's edge node
2. Hub monitors VWC readings for that zone
3. When VWC reaches `vwc_high` (configured target), hub sends "close valve"
4. If `vwc_high` is not reached within the maximum duration (default: 30 minutes), hub closes the valve anyway and generates an alert
5. **Single-zone invariant**: the hub rejects any command that would open a second valve while one is already open

### AI Mode vs. Rule-Based Mode
Toggle in [AI Settings](../dashboard/settings.md#ai-settings). In AI mode, recommendations come from the ONNX irrigation model trained on zone sensor history. In rule-based mode, threshold logic generates recommendations. Both use the same approve/reject UX.

### Recommendation Back-Off
After a farmer rejects a recommendation, a configurable back-off window (default: 2 hours) prevents the same recommendation type from re-appearing for that zone. This is separate from the cool-down window applied after approval.

## Coop Door Scheduling

### Automatic Schedule
The bridge calculates sunrise and sunset for the configured lat/long using the NOAA astronomical algorithm (Python `astral` library). Schedule runs daily:
- **Open**: sunrise + `open_offset_min` minutes, but no earlier than `hard_open_limit`
- **Close**: sunset + `close_offset_min` minutes, but no later than `hard_close_limit`

### Limit Switch Safety
Every open/close command waits for limit switch confirmation from the edge node:
- Door open command → hub waits for "fully open" limit switch signal within 60 seconds
- Door close command → hub waits for "fully closed" limit switch signal within 60 seconds
- If confirmation is not received: `stuck_door` P0 alert fires; no further commands are sent automatically

### Manual Override
The **Open Door** / **Close Door** buttons on the [Coop Panel](../dashboard/coop.md) send immediate manual commands, bypassing the schedule. The limit switch safety check still applies.

## Flock Production Model

Expected daily egg production is calculated as:

```
expected = flock_size × breed_lay_rate × age_factor × daylight_factor
```

| Factor | Description |
|--------|-------------|
| `breed_lay_rate` | Base rate for the configured breed (e.g., Leghorn = 0.85 eggs/hen/day) |
| `age_factor` | 0.0 before 18 weeks; ramps to 1.0 by 24 weeks; 0.9 at 18 months; 0.7 at 36 months |
| `daylight_factor` | Fraction of 14 hours actual daylight (or 1.0 if supplemental lighting is enabled) |

The **production drop alert** fires when the 3-day rolling average of actual eggs falls below 75% of the expected value for 3 consecutive days.

See [Coop Configuration](coop.md#flock-configuration) for the configurable inputs to this model.
