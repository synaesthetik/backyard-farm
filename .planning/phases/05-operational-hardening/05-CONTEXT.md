# Phase 5: Operational Hardening - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

The system survives daily use over months -- pH sensors are calibrated on schedule, sensor calibration offsets are managed from the hub, push notifications reach the farmer's phone via self-hosted ntfy, and data retention policies prevent unbounded storage growth.

This phase delivers:
- pH calibration date tracking with 2-week overdue reminders in the alert bar
- Calibration recording workflow (farmer confirms calibration, offset updates)
- Per-sensor calibration management UI (dry/wet values, temp coefficient)
- Self-hosted ntfy push notification integration (external server, optional/additive)
- ntfy configuration in dashboard + env vars
- Data retention policies (90-day raw purge, 2-year hourly rollups)
- Storage usage display on a dedicated settings section

Phase 5 does NOT deliver: hardware shopping list (Phase 6), user tutorial (Phase 7), or any new sensor types.

</domain>

<decisions>
## Implementation Decisions

### pH Calibration Workflow (ZONE-07)

- **D-01: pH calibration reminder appears in the alert bar as P1 (amber).** Same pattern as low moisture, stuck door, etc. "pH calibration overdue -- Zone A" uses the existing AlertEngine hysteresis pattern. Alert fires when `last_calibration_date` is older than 2 weeks, clears when the farmer records a new calibration.
- **D-02: Calibration recording UX is Claude's discretion.** Choose the right approach based on the existing zone detail page structure -- either a button on /zones/[id] next to the pH row, or a dedicated calibration management page, whichever integrates more naturally.
- **D-03: New column `last_calibration_date` on `calibration_offsets` table.** Nullable TIMESTAMPTZ. When the farmer records a calibration, this is set to NOW(). The bridge checks this field during alert evaluation to determine if a reminder is needed.

### Sensor Calibration Management (05-02)

- **D-04: Calibration is hub-only -- no edge push needed.** The existing CalibrationStore applies offsets at ingestion on the hub side. Edge nodes send raw values. When the farmer updates dry/wet values or temp coefficient, the hub's in-memory cache is refreshed. No MQTT config push to edge nodes required.
- **D-05: Calibration management UI shows per-sensor offsets, dry/wet values, temp coefficient, and last calibration date.** The farmer can view and edit these values. Changes take effect on the next sensor reading (CalibrationStore reload).

### ntfy Push Notifications (NOTF-03)

- **D-06: External ntfy server -- farmer provides URL.** No ntfy Docker container in the compose stack. The bridge sends HTTP POST to the farmer's ntfy server (could be ntfy.sh public or their own instance). Configuration is a URL + topic.
- **D-07: Env vars set defaults, dashboard settings page overrides at runtime.** `NTFY_URL` and `NTFY_TOPIC` in hub.env provide the initial configuration. A settings page (/settings/notifications or similar) lets the farmer update URL, topic, and toggle on/off without restarting. Include a "Send Test" button.
- **D-08: ntfy fires for the same events that trigger in-app alerts.** Same event list as AlertEngine output: low moisture, pH out of range, low feed/water, production drop, stuck coop door, node offline, pH calibration overdue. In-app alerts remain the baseline; ntfy is purely additive.
- **D-09: ntfy is optional -- system works fully without it.** If NTFY_URL is empty/unset, ntfy is silently disabled. No errors, no warnings. The farmer can enable it later at any time.

### Data Retention Policies (05-03)

- **D-10: TimescaleDB built-in retention policies for automated purge.** Use `add_retention_policy()` on the `sensor_readings` hypertable with a 90-day interval. Raw data older than 90 days is dropped automatically by TimescaleDB's background worker.
- **D-11: Hourly rollup via TimescaleDB continuous aggregate.** Create a continuous aggregate `sensor_readings_hourly` that computes avg, min, max per (zone_id, sensor_type) per hour. Retained for 2 years (730 days). This provides historical trend data after raw data is purged.
- **D-12: Dedicated storage section on a settings page.** Shows per-table sizes (raw readings, rollups, egg counts, etc.), retention policy status, last purge date, and a manual "Purge Now" button. More than just a stat line -- the farmer has visibility and control.

### Claude's Discretion

- pH calibration recording UX placement (zone detail button vs dedicated page)
- Calibration management page layout and route path
- ntfy HTTP POST format (ntfy supports simple POST with title/body/priority headers)
- ntfy settings page route (/settings/notifications or part of existing /settings/ai)
- Continuous aggregate refresh policy interval
- Storage section page layout and route
- Whether to include a "Purge Now" confirmation dialog

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 5 Core
- `.planning/ROADMAP.md` -- Phase 5 goal, success criteria, 4 pre-defined plans (05-01 through 05-04)
- `.planning/REQUIREMENTS.md` -- Full requirement text for ZONE-07, NOTF-03

### Existing Code (must read before planning)
- `hub/bridge/calibration.py` -- CalibrationStore with in-memory cache; Phase 5 extends with last_calibration_date tracking
- `hub/bridge/alert_engine.py` -- AlertEngine with hysteresis; Phase 5 adds pH calibration overdue alert type
- `hub/bridge/main.py` -- Bridge pipeline; ntfy integration hooks into the alert broadcast path
- `hub/init-db.sql` -- calibration_offsets table schema; needs last_calibration_date column, plus continuous aggregate DDL
- `hub/api/main.py` -- FastAPI server; new routes for calibration management and ntfy settings
- `hub/dashboard/src/lib/AlertBar.svelte` -- Alert bar component; pH calibration alerts render here
- `hub/dashboard/src/lib/ws.svelte.ts` -- WebSocket store; extend for calibration and ntfy state

### Prior Phase Patterns
- `.planning/phases/04-onnx-ai-layer-and-recommendation-engine/04-CONTEXT.md` -- AI settings page pattern (D-05, D-06, D-07) reusable for ntfy settings
- `hub/api/inference_settings_router.py` -- Settings endpoint pattern (GET/PATCH proxy to bridge) reusable for ntfy and calibration endpoints
- `hub/bridge/inference/ai_settings.py` -- JSON sidecar persistence pattern reusable for ntfy settings

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CalibrationStore` -- Already loads offsets from DB. Extend with `last_calibration_date` field and an `is_overdue(zone_id, sensor_type)` method.
- `AlertEngine` -- Extend with `ph_calibration_overdue` alert type. Same hysteresis pattern (fires on overdue, clears on calibration recorded).
- `AISettings` pattern -- JSON sidecar persistence in `ai_settings.py` is directly reusable for ntfy settings (URL, topic, enabled).
- `inference_settings_router.py` -- GET/PATCH proxy pattern reusable for calibration and ntfy endpoints.
- TimescaleDB `add_retention_policy()` and `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` -- built-in features, no custom code needed for the purge/rollup engine.

### Established Patterns
- Settings endpoint: GET returns current state, PATCH updates one field, proxy to bridge internal HTTP server
- Alert flow: bridge evaluates -> broadcasts delta -> dashboard AlertBar renders
- Dashboard settings pages: /settings/ai exists as the pattern for /settings/notifications and /settings/storage

### Integration Points
- `hub/init-db.sql` -- ALTER TABLE calibration_offsets ADD COLUMN last_calibration_date; CREATE continuous aggregate
- `hub/bridge/main.py` -- ntfy HTTP POST in the alert broadcast path
- `hub/api/main.py` -- mount calibration and ntfy routers
- `hub/dashboard/src/routes/settings/` -- new notification and storage settings routes

</code_context>

<specifics>
## Specific Ideas

- ntfy settings page should include a "Send Test" button so the farmer can verify their phone receives notifications before relying on it.
- Storage section should show actual TimescaleDB table sizes, not just config -- the farmer wants to see "2.3 GB used" not just "90-day retention enabled."
- pH calibration overdue alert should deep-link to the zone where calibration is needed.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 05-operational-hardening*
*Context gathered: 2026-04-15*
