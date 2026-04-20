# Zone Configuration

**Route:** `/settings/zones`

Each zone corresponds to a physical garden bed with its own edge node sensors.

## Zone Properties

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `name` | string | Human-readable zone name (e.g., "Tomatoes", "Herb Garden") | Required |
| `zone_id` | string | Internal identifier, used in MQTT topics and irrigation commands | Required |
| `soil_type` | enum | `loam`, `clay`, `sandy`, `peat` | `loam` |
| `vwc_low` | float (%) | Low VWC threshold — triggers irrigation recommendation | 25.0 |
| `vwc_high` | float (%) | High VWC threshold — upper bound for sensor-feedback irrigation loop | 60.0 |
| `ph_min` | float | Minimum acceptable pH — triggers ph_low alert | 5.5 |
| `ph_max` | float | Maximum acceptable pH — triggers ph_high alert | 7.5 |
| `temp_min_c` | float (°C) | Minimum temperature — triggers temp_low alert | 5.0 |
| `temp_max_c` | float (°C) | Maximum temperature — triggers temp_high alert | 35.0 |
| `irrigation_zone_id` | string | Relay/valve identifier — maps to edge node GPIO relay number | Required |
| `calibration_dry` | float | Soil sensor dry ADC reading (used for VWC conversion) | 2.8 |
| `calibration_wet` | float | Soil sensor wet ADC reading | 1.2 |

## Adding a Zone
Click **Add Zone** in the Zones settings page. Enter the zone name and irrigation zone ID (must match the relay number physically wired to that zone's solenoid valve). The zone will appear on the home screen once the edge node publishes its first reading.

## Editing and Deleting
Tap the zone name to edit its configuration. Deleting a zone removes all zone metadata but retains historical sensor data in TimescaleDB.

## Alert Thresholds
The `vwc_low`, `ph_min`, `ph_max`, `temp_min_c`, and `temp_max_c` values directly control when alerts fire. See [Alerts and Notifications](alerts.md) for the full alert behavior including hysteresis bands.

## Soil Sensor Calibration
The `calibration_dry` and `calibration_wet` ADC values are used to convert raw voltage readings to VWC percentages. If your sensor reads 0% or 100% even with normal soil conditions, re-run the two-point calibration:
1. Insert probe into completely dry soil — record the ADC voltage as `calibration_dry`
2. Insert probe into saturated soil — record the ADC voltage as `calibration_wet`

See [Garden Node hardware docs](../hardware/garden-node.md) for the physical calibration procedure.
