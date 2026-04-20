# Alerts and Notifications

Alerts appear in the persistent **Alert Bar** at the top of every dashboard screen. P0 alerts are shown in red and indicate an immediate problem requiring action. P1 alerts are shown in yellow and indicate a condition requiring attention.

## Alert Behavior

All alerts have **debounce and hysteresis** applied:
- An alert fires when a value **crosses the threshold** (not on every reading)
- An alert clears only when the value **recovers past the hysteresis band** (prevents alert storms on sensor noise)
- Tapping an alert bar item navigates to the relevant zone or component
- Multiple alerts of the same type across zones are grouped (e.g., "Low moisture — 3 zones")

## Alert Types

### P0 Alerts: Critical

| Alert Key | Trigger | Message | Hysteresis | Resolution |
|-----------|---------|---------|-----------|-----------|
| `stuck_door` | Coop door limit switch not reached within 60 seconds of open/close command | "Coop door stuck" | N/A (manual reset) | Check door mechanism; see [Coop Node](../hardware/coop-node.md) smoke test |
| `node_offline` | Edge node misses 3 consecutive 60-second heartbeats (≥3 min offline) | "Node offline — {node_id}" | N/A (clears on reconnect) | Check power and Wi-Fi; see [Troubleshooting](../troubleshooting/index.md) |

### P1 Alerts: Warning

| Alert Key | Trigger | Message | Hysteresis | Resolution |
|-----------|---------|---------|-----------|-----------|
| `moisture_low` | Zone VWC < configured `vwc_low` threshold | "Low moisture — {zone_id}" | +5% VWC | Irrigate or approve pending recommendation |
| `ph_low` | Zone pH < configured `ph_min` | "Low pH — {zone_id}" | +0.2 pH | Add lime; check calibration |
| `ph_high` | Zone pH > configured `ph_max` | "High pH — {zone_id}" | −0.2 pH | Add sulfur; check calibration |
| `temp_low` | Zone temperature < configured `temp_min_c` | "Low temperature — {zone_id}" | +2.0 °C | Frost protection; check for sensor fault |
| `temp_high` | Zone temperature > configured `temp_max_c` | "High temperature — {zone_id}" | −2.0 °C | Shade or ventilation |
| `feed_low` | Feed fill% < configured `feed_low_threshold` | "Low feed level" | +5% | Refill feeder |
| `water_low` | Water fill% < configured `water_low_threshold` | "Low water level" | +5% | Check water supply |
| `production_drop` | 3-day rolling average eggs < 75% of expected | "Production drop — eggs below expected" | +10% recovery | Review flock health; check coop conditions |
| `feed_consumption_drop` | Daily feed consumption drops >2 std deviations below recent average | "Feed consumption drop" | +5% | Check feeder mechanism; review flock health |
| `ph_calibration_overdue` | pH sensor last calibration > 14 days ago | "pH calibration overdue — {zone_id}" | N/A (clears on calibration record) | Perform two-point calibration; see [Calibration Settings](../dashboard/settings.md#calibration) |

## Threshold Configuration

Alert thresholds for zone sensors (`vwc_low`, `ph_min`, `ph_max`, `temp_min_c`, `temp_max_c`) are configured per zone in [Zone Configuration](zones.md).

Thresholds for feed and water (`feed_low_threshold`, `water_low_threshold`) are configured in [Coop Configuration](coop.md#feed-and-water-thresholds).

## Push Notifications (ntfy)

If ntfy is configured in Settings → Notifications, the same events that trigger in-app alerts also send a push notification to your phone. In-app alerts are always active — ntfy is additive only. See [Notifications Settings](../dashboard/settings.md#notifications).
