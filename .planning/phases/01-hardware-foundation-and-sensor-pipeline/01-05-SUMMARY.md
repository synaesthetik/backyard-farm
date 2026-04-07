---
phase: 01-hardware-foundation-and-sensor-pipeline
plan: "05"
subsystem: bridge
tags: [mqtt, timescaledb, fastapi, websocket, quality-flags, calibration, stuck-detection, heartbeat, asyncpg, aiomqtt, pydantic]

requires:
  - phase: 01-hardware-foundation-and-sensor-pipeline
    plan: "01"
    provides: "TimescaleDB schema (sensor_readings, calibration_offsets, node_heartbeats hypertables), FastAPI skeleton"
  - phase: 01-hardware-foundation-and-sensor-pipeline
    plan: "02"
    provides: "MQTT topic schema (farm/+/sensors/#, farm/+/heartbeat), hub-bridge credentials"

provides:
  - "Hub MQTT bridge subscribing to farm/+/sensors/# and farm/+/heartbeat"
  - "Quality flag pipeline: range-based GOOD/SUSPECT/BAD per sensor type (D-10, D-11)"
  - "Calibration offset application at ingestion per ZONE-03"
  - "Stuck-reading detection: 30+ consecutive identical values flags STUCK boolean (D-12)"
  - "TimescaleDB write pipeline: sensor_readings and node_heartbeats hypertable inserts"
  - "FastAPI WebSocket endpoint at /ws/dashboard with snapshot-on-connect and delta broadcast"
  - "FastAPI internal /internal/notify POST endpoint receiving bridge deltas"
  - "25 unit tests covering all quality ranges, stuck detection, calibration, and heartbeat models"

affects: [01-06]

tech-stack:
  added:
    - aiohttp==3.11.18 (bridge internal HTTP notify to API)
  patterns:
    - "Bridge pipeline pattern: parse -> calibrate -> quality-flag -> stuck-check -> DB insert -> HTTP notify"
    - "WebSocket snapshot-on-connect: full state sent to new clients, then deltas only (D-16)"
    - "StuckDetector: per-(zone_id, sensor_type) counter dict; resets on value change"
    - "CalibrationStore: in-memory dict loaded from DB on startup; set_offset for testing"
    - "Quality ranges configurable via env vars (MOISTURE_BAD_MIN etc.) per D-11"
    - "Internal HTTP bridge-to-API: aiohttp POST to /internal/notify; failures are non-fatal"

key-files:
  created:
    - hub/bridge/models.py
    - hub/bridge/quality.py
    - hub/bridge/calibration.py
    - hub/bridge/tests/__init__.py
    - hub/bridge/tests/conftest.py
    - hub/bridge/tests/test_quality.py
    - hub/bridge/tests/test_calibration.py
    - hub/bridge/tests/test_heartbeat.py
    - hub/api/ws_manager.py
    - hub/api/models.py
  modified:
    - hub/bridge/main.py
    - hub/bridge/requirements.txt
    - hub/api/main.py

key-decisions:
  - "Quality flags applied on calibrated value (not raw) — calibration corrects the reading, flag evaluates correctness"
  - "STUCK is a display-only boolean that does NOT downgrade the quality flag per D-12"
  - "Bridge notifies API via internal HTTP (aiohttp POST) rather than direct import — keeps bridge and API decoupled in Docker"
  - "WebSocket manager holds in-memory state snapshot (zone_states, node_states) to send full snapshot on connect per D-16"
  - "aiohttp==3.11.18 added to bridge requirements for internal API notification"

requirements-completed: [INFRA-02, INFRA-05, INFRA-06, INFRA-07, ZONE-03]

duration: 3min
completed: 2026-04-07
---

# Phase 01 Plan 05: Hub MQTT Bridge Summary

**Complete MQTT bridge pipeline applying calibration offsets, quality flags, and stuck detection at ingestion, writing to TimescaleDB, with FastAPI WebSocket manager for real-time dashboard push**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-07T19:05:48Z
- **Completed:** 2026-04-07T19:08:24Z
- **Tasks:** 2/2
- **Files modified:** 10 created, 3 modified

## Accomplishments

- Quality flag logic (D-10, D-11): range-based GOOD/SUSPECT/BAD for moisture, pH, temperature; unknown sensors default to GOOD; ranges configurable via env vars
- Stuck detection (D-12): StuckDetector class tracks consecutive identical values per (zone_id, sensor_type); flags at 30+ identical readings; STUCK does not affect quality flag
- CalibrationStore (ZONE-03): in-memory offset cache loaded from TimescaleDB calibration_offsets table on startup; apply_calibration returns (calibrated_value, applied_bool)
- Full bridge pipeline in main.py: JSON parse -> Pydantic validation -> calibrate -> quality flag -> stuck check -> asyncpg INSERT -> aiohttp notify
- WebSocketManager: snapshot-on-connect (full zone/node state), delta broadcast to all clients, auto-disconnect cleanup
- FastAPI updated with /ws/dashboard WebSocket endpoint and /internal/notify POST endpoint
- 25 unit tests: 18 quality/stuck, 4 calibration, 3 heartbeat — all pass

## Task Commits

1. **Task 1: Quality flag logic, calibration store, and stuck detection with tests** - `2ecb09d` (feat)
2. **Task 2: MQTT bridge pipeline, heartbeat tracker, and WebSocket manager** - `2ec1117` (feat)

## Files Created/Modified

- `hub/bridge/models.py` - QualityFlag enum, SensorPayload, HeartbeatPayload, ProcessedReading Pydantic models
- `hub/bridge/quality.py` - apply_quality_flag range checks and StuckDetector class
- `hub/bridge/calibration.py` - CalibrationStore with async DB load and apply_calibration
- `hub/bridge/main.py` - Full MQTT bridge pipeline (replaces placeholder stub)
- `hub/bridge/requirements.txt` - Added aiohttp==3.11.18
- `hub/bridge/tests/test_quality.py` - 18 tests: moisture/pH/temperature ranges, boundary values, stuck detection
- `hub/bridge/tests/test_calibration.py` - 4 tests: positive/negative/zero offset, missing record
- `hub/bridge/tests/test_heartbeat.py` - 3 tests: payload validation, missing field, delta format
- `hub/api/ws_manager.py` - WebSocketManager with snapshot-on-connect and broadcast
- `hub/api/models.py` - HealthResponse and NotifyPayload Pydantic models
- `hub/api/main.py` - Added /ws/dashboard WebSocket and /internal/notify POST endpoints

## Decisions Made

- Quality flags are applied to the **calibrated** value, not the raw sensor value — the calibration corrects the reading before the range check evaluates it
- STUCK boolean is a display-only state that does NOT downgrade GOOD quality flags (D-12) — GOOD+STUCK readings remain usable for Phase 4 model training
- Bridge-to-API communication uses internal HTTP (aiohttp POST to /internal/notify) rather than direct Python import — maintains Docker service isolation; failures are silently swallowed as non-critical
- WebSocketManager holds in-memory zone/node state dict to fulfil snapshot-on-connect requirement (D-16) without a database query per connection

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — all pipeline components are fully implemented. The placeholder bridge/main.py stub from plan 01-01 has been replaced with the complete implementation.

## Issues Encountered

None.

## User Setup Required

None — bridge service is fully self-contained. When Docker Compose starts:
1. Bridge connects to Mosquitto using `MQTT_BRIDGE_USER` / `MQTT_BRIDGE_PASS` env vars from hub.env
2. Bridge connects to TimescaleDB using `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` env vars
3. CalibrationStore loads existing calibration offsets on startup (empty table is fine — no offsets = pass-through)

## Next Phase Readiness

- Plan 01-06 (dashboard components) can proceed — WebSocket endpoint at /ws/dashboard is live, snapshot-on-connect is implemented, delta format is defined
- All sensor data will flow through the quality/calibration pipeline before reaching TimescaleDB or the dashboard

---
*Phase: 01-hardware-foundation-and-sensor-pipeline*
*Completed: 2026-04-07*

## Self-Check: PASSED

- hub/bridge/models.py: FOUND
- hub/bridge/quality.py: FOUND
- hub/bridge/calibration.py: FOUND
- hub/bridge/tests/__init__.py: FOUND
- hub/bridge/tests/conftest.py: FOUND
- hub/bridge/tests/test_quality.py: FOUND
- hub/bridge/tests/test_calibration.py: FOUND
- hub/bridge/tests/test_heartbeat.py: FOUND
- hub/api/ws_manager.py: FOUND
- hub/api/models.py: FOUND
- hub/bridge/main.py: FOUND
- hub/bridge/requirements.txt: FOUND
- hub/api/main.py: FOUND
- Commit 2ecb09d: FOUND
- Commit 2ec1117: FOUND
