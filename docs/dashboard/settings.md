# Settings Screens

Settings are grouped under `/settings/*`. Navigate via the Settings tab bar.

## AI Settings

**Route:** `/settings/ai`

- **AI Engine toggle** — Enable or disable the ONNX AI engine. When disabled, the rule-based recommendation engine is active.
- **Domain status** — Each AI domain (zone health, irrigation, flock anomaly) shows its model maturity: recommendation count, approval rate, and whether the model is past cold-start
- **Maturity thresholds** — Read-only display of minimum sample counts required before each domain is considered mature

## Calibration

**Route:** `/settings/calibration`

Lists pH calibration records for every zone:
- Zone name, sensor ID, last calibration date, next due date
- Overdue zones are highlighted in yellow/orange
- **Record Calibration** button — enter the new offset value (derived from your two-point calibration using pH 4.0 and 7.0 buffer solutions). See [hardware/garden-node.md](../hardware/garden-node.md) for the calibration procedure.

A [`ph_calibration_overdue`](../configuration/alerts.md#p1-alerts-warning) alert fires automatically when calibration is more than 14 days past due.

## Notifications

**Route:** `/settings/notifications`

- **ntfy server URL** — Self-hosted ntfy instance URL (e.g., `https://ntfy.your-server.com`)
- **ntfy topic** — The topic name your phone is subscribed to
- **Test notification** button — Sends a test push to confirm delivery
- ntfy is optional. In-app alerts in the alert bar are always active regardless of ntfy configuration.

See [ntfy documentation](https://ntfy.sh/docs/) for setting up a self-hosted ntfy server.

## Storage

**Route:** `/settings/storage`

- **Database statistics** — Current row counts and estimated disk usage for raw sensor readings, hourly rollups, and alert history
- **Retention summary** — Raw readings: 90-day retention. Hourly rollups: 2-year retention.
- **Manual purge** — Trigger a manual cleanup run for rows past their retention period (this also runs automatically every 24 hours)

## Tutorial

Links to `/tutorial/1`. Restarts the interactive tutorial from the beginning. If you dismissed the auto-launch banner on first visit, use this to start the tutorial at any time.
