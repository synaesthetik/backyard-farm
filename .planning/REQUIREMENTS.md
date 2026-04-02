# Requirements: Backyard Farm Platform

**Defined:** 2026-04-01
**Core Value:** A single dashboard where you can see every zone's sensor readings, irrigation status, and flock health at a glance — and act on AI recommendations without leaving it.

## v1 Requirements

### Infrastructure

- [ ] **INFRA-01**: Hub service stack runs via Docker Compose (Mosquitto, TimescaleDB, FastAPI, Caddy) on a local machine — no cloud dependency
- [ ] **INFRA-02**: Edge nodes publish sensor readings via MQTT with QoS 1; hub subscribes and writes to TimescaleDB with quality flags (GOOD / SUSPECT / BAD) applied at ingestion
- [ ] **INFRA-03**: Each edge node maintains a local SQLite buffer; data is flushed to hub on reconnect with original timestamps preserved
- [ ] **INFRA-04**: Edge nodes run a local rule engine that executes emergency-threshold actions (coop door fallback, emergency irrigation shutoff) without hub involvement
- [ ] **INFRA-05**: Hub monitors edge node heartbeats; alerts if a node misses 3 consecutive 60-second heartbeats
- [ ] **INFRA-06**: All sensor readings displayed with a freshness timestamp; readings older than 5 minutes are flagged as stale in the UI
- [ ] **INFRA-07**: Static-reading detection flags sensors returning the same value for 30+ consecutive readings
- [ ] **INFRA-08**: MQTT topic schema and per-node ACL credentials are defined and documented before any node software is written
- [ ] **INFRA-09**: Hub serves local HTTPS via Caddy (required for PWA install on iOS)

### Garden Zones

- [ ] **ZONE-01**: Each garden zone has configurable metadata: plant type, soil type, target VWC range, pH target range, irrigation zone ID
- [ ] **ZONE-02**: Zone nodes poll soil moisture (VWC %), pH, and temperature sensors on a configurable interval and publish via MQTT
- [ ] **ZONE-03**: Hub applies per-sensor calibration offsets (dry/wet values, temperature coefficient) at ingestion before writing to TimescaleDB
- [ ] **ZONE-04**: Dashboard shows live sensor readings per zone with freshness timestamp and quality flag indicator
- [ ] **ZONE-05**: Dashboard shows 7-day and 30-day sensor history graphs per zone
- [ ] **ZONE-06**: Each zone displays a composite health score (green / yellow / red) derived from moisture, pH, and temperature readings vs. configured targets
- [ ] **ZONE-07**: pH calibration workflow: tracks calibration date per sensor, shows due-date reminder when calibration is overdue (2-week cadence), records calibration offset on hub

### Irrigation

- [ ] **IRRIG-01**: Dashboard supports manual irrigation control per zone (open / close valve command routed hub → edge node → relay)
- [ ] **IRRIG-02**: Hub enforces single-zone-at-a-time invariant — rejects commands that would open multiple zones simultaneously
- [ ] **IRRIG-03**: All irrigation valves are normally-closed (NC) solenoids — procurement requirement documented for hardware selection
- [ ] **IRRIG-04**: Threshold-based irrigation recommendations generated when zone VWC drops below the low threshold; displayed in recommendation queue for farmer approval
- [ ] **IRRIG-05**: Sensor-feedback irrigation loop: once approved, hub commands valve open and monitors VWC; closes valve when target VWC is reached or max duration exceeded
- [ ] **IRRIG-06**: Irrigation recommendations are suppressed during a cool-down window after a recent irrigation event (prevent re-triggering on lag sensor readings)

### Coop Automation

- [ ] **COOP-01**: Coop door opens at sunrise and closes at sunset, calculated from configured latitude/longitude (NOAA astronomical clock); configurable offset in minutes
- [ ] **COOP-02**: Coop door has hard time limits as safety backstop (e.g., force-close no later than 21:00 regardless of sunset calculation)
- [ ] **COOP-03**: All coop door commands require physical limit switch confirmation; if the expected limit switch is not reached within 60 seconds of command, alert is raised and no further commands are sent
- [ ] **COOP-04**: Coop door actuator uses a linear actuator with physical limit switches at fully-open and fully-closed positions — procurement requirement documented for hardware selection
- [ ] **COOP-05**: Dashboard shows coop door current state (open / closed / moving / stuck) with manual open/close override
- [ ] **COOP-06**: Feed level sensor (load cell preferred) monitors hopper weight; dashboard shows current fill percentage and triggers alert when below configured low threshold
- [ ] **COOP-07**: Water level monitoring with low-level alert

### Flock Management

- [ ] **FLOCK-01**: Farmer can enter daily egg count via dashboard; counts are stored per day
- [ ] **FLOCK-02**: Expected production model calculates daily expected egg count from: configured flock size × breed lay rate × age factor × daylight hours factor
- [ ] **FLOCK-03**: Dashboard shows egg production trend chart (actual vs. expected) over 30 days
- [ ] **FLOCK-04**: Production drop alert triggered when 3-day rolling average falls below 75% of expected; displayed in alert bar
- [ ] **FLOCK-05**: Flock configuration: breed, hatch date (for age factor), flock size, supplemental lighting on/off
- [ ] **FLOCK-06**: Feed consumption rate tracked from load cell data (daily consumption derived from weight delta)

### AI & Recommendations

- [ ] **AI-01**: Recommendation queue UI shows pending recommendations with: action description, supporting sensor values, explanation of why recommended; farmer can approve or reject each
- [ ] **AI-02**: Rule-based recommendation engine (Phase 2) generates irrigation and coop recommendations from threshold logic; same UX as ML-backed recommendations
- [ ] **AI-03**: ONNX Runtime models (Phase 4) replace rule engine for zone health scoring, irrigation schedule optimization, and flock production anomaly detection
- [ ] **AI-04**: Recommendations are deduplicated: if a pending recommendation of the same type exists for a zone, new duplicates are suppressed until the pending one is resolved
- [ ] **AI-05**: After rejection, a back-off window prevents the same recommendation type from appearing again for a configurable period
- [ ] **AI-06**: AI training uses only GOOD-quality-flagged sensor data; raw or SUSPECT readings are excluded from model training datasets
- [ ] **AI-07**: Model maturity indicator in UI: shows recommendation count and approval/rejection rate per recommendation type (manages user expectations during cold start)

### Dashboard & UI

- [ ] **UI-01**: Single overview screen shows all garden zones (composite health, current moisture) and flock summary (door status, egg count today, production trend) in one view
- [ ] **UI-02**: P0/P1 alert bar is persistent on all screens; groups duplicate alert types; shows count if multiple alerts of same type exist
- [ ] **UI-03**: Alert bar items are tappable and route to the relevant zone or component detail screen
- [ ] **UI-04**: Web dashboard is accessible from any browser on the local network via HTTPS
- [ ] **UI-05**: Dashboard is a PWA installable on iOS and Android (service worker with offline shell; requires HTTPS)
- [ ] **UI-06**: Dashboard is usable on a phone screen in the yard (mobile-first responsive layout)
- [ ] **UI-07**: System health panel shows: each node's online/offline status, last heartbeat timestamp, and data freshness indicator

### Notifications

- [ ] **NOTF-01**: In-app alerts displayed in the persistent alert bar for: low moisture, pH out of range, low feed/water, production drop, stuck coop door, node offline
- [ ] **NOTF-02**: Alert debounce and hysteresis prevent alert storms (alert fires on crossing threshold, clears only when value recovers past hysteresis band)
- [ ] **NOTF-03**: Self-hosted push notifications via ntfy (optional V1 stretch goal — in-app alerts are the baseline)

---

## v2 Requirements

### Advanced AI

- **AI2-01**: LSTM or gradient-boosted predictive irrigation scheduling trained on 4+ weeks of historical data (sensor-feedback loop is V1; predictive scheduling is V2)
- **AI2-02**: Per-rejection reason tagging to improve recommendation quality over time
- **AI2-03**: Behavioral anomaly detection for flock (requires motion sensors in coop — additional hardware)

### Advanced Sensors

- **SENS2-01**: Nutrient / EC sensor integration per zone (expensive, high maintenance — validate V1 value before adding)
- **SENS2-02**: Computer vision / camera-based plant health assessment (sensor-based is V1; camera is V2)
- **SENS2-03**: Weather station integration for ET-based irrigation refinement

### Operations

- **OPS2-01**: OTA firmware update system for edge nodes (hub-served packages, MQTT-triggered, SHA256-verified)
- **OPS2-02**: Node re-image and reconfigure automation (zero-manual-steps recovery)
- **OPS2-03**: Frost prediction alerts via local weather data

### Analytics

- **ANLT2-01**: Zone-to-zone comparison analytics (requires data accumulation from V1)
- **ANLT2-02**: Seasonal yield projections and harvest planning

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud sync or remote access | Hard constraint — local-only by design; privacy, reliability, no recurring cost |
| External push notifications (Firebase, APNs) | Cloud dependency; ntfy self-hosted is the local alternative |
| Fully autonomous irrigation without approval | Intentional design choice — recommend-and-confirm in v1; autonomy tuned later |
| OAuth / SSO login | Single-user, LAN system; shared passphrase + JWT is correctly-sized |
| Computer vision / camera plant health | Sensor-based chosen for v1; cameras deferred to v2 |
| Commercial-scale features | Backyard / medium hobby scale only — not multi-tenant, not fleet management |
| Companion planting guidance | Low priority, not actionable at sensor level |
| Real-time chat / social features | Out of domain |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INFRA-04 | Phase 1 | Pending |
| INFRA-05 | Phase 1 | Pending |
| INFRA-06 | Phase 1 | Pending |
| INFRA-07 | Phase 1 | Pending |
| INFRA-08 | Phase 1 | Pending |
| INFRA-09 | Phase 1 | Pending |
| ZONE-01 | Phase 1 | Pending |
| ZONE-02 | Phase 1 | Pending |
| ZONE-03 | Phase 1 | Pending |
| ZONE-04 | Phase 1 | Pending |
| ZONE-05 | Phase 2 | Pending |
| ZONE-06 | Phase 2 | Pending |
| ZONE-07 | Phase 5 | Pending |
| IRRIG-01 | Phase 2 | Pending |
| IRRIG-02 | Phase 2 | Pending |
| IRRIG-03 | Phase 1 | Pending |
| IRRIG-04 | Phase 2 | Pending |
| IRRIG-05 | Phase 2 | Pending |
| IRRIG-06 | Phase 2 | Pending |
| COOP-01 | Phase 2 | Pending |
| COOP-02 | Phase 2 | Pending |
| COOP-03 | Phase 2 | Pending |
| COOP-04 | Phase 1 | Pending |
| COOP-05 | Phase 2 | Pending |
| COOP-06 | Phase 2 | Pending |
| COOP-07 | Phase 2 | Pending |
| FLOCK-01 | Phase 3 | Pending |
| FLOCK-02 | Phase 3 | Pending |
| FLOCK-03 | Phase 3 | Pending |
| FLOCK-04 | Phase 3 | Pending |
| FLOCK-05 | Phase 3 | Pending |
| FLOCK-06 | Phase 3 | Pending |
| AI-01 | Phase 2 | Pending |
| AI-02 | Phase 2 | Pending |
| AI-03 | Phase 4 | Pending |
| AI-04 | Phase 2 | Pending |
| AI-05 | Phase 2 | Pending |
| AI-06 | Phase 4 | Pending |
| AI-07 | Phase 4 | Pending |
| UI-01 | Phase 3 | Pending |
| UI-02 | Phase 2 | Pending |
| UI-03 | Phase 2 | Pending |
| UI-04 | Phase 1 | Pending |
| UI-05 | Phase 2 | Pending |
| UI-06 | Phase 2 | Pending |
| UI-07 | Phase 1 | Pending |
| NOTF-01 | Phase 2 | Pending |
| NOTF-02 | Phase 2 | Pending |
| NOTF-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after initial definition*
