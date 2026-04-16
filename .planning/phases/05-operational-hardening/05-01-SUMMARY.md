---
phase: 05-operational-hardening
plan: 01
subsystem: calibration
tags: [calibration, alerts, timescaledb, bridge, api]
dependency_graph:
  requires: []
  provides:
    - CalibrationStore.is_overdue
    - CalibrationStore.record_calibration
    - CalibrationStore.get_all_calibrations
    - AlertEngine ph_calibration_overdue
    - periodic_calibration_check loop
    - /api/calibrations REST endpoints
  affects:
    - hub/bridge/main.py (new coroutine in gather, new internal HTTP handlers)
    - hub/api/main.py (new router mounted)
tech_stack:
  added: []
  patterns:
    - TDD (RED-GREEN) for CalibrationStore and AlertEngine extensions
    - aiohttp proxy pattern (mirrors inference_settings_router.py)
    - Pydantic BaseModel validation at API boundary (T-05-01)
    - DO-block idempotency wrappers for TimescaleDB cagg DDL
key_files:
  created:
    - hub/migrations/05-calibration-and-retention.sql
    - hub/api/calibration_router.py
  modified:
    - hub/bridge/calibration.py
    - hub/bridge/alert_engine.py
    - hub/bridge/main.py
    - hub/api/main.py
    - hub/init-db.sql
    - hub/bridge/tests/test_calibration.py
    - hub/bridge/tests/test_alert_engine.py
decisions:
  - "Boundary test for is_overdue adjusted by +5s to avoid microsecond timing drift in CI (plan spec: overdue is strictly >14 days)"
  - "TimescaleDB cagg DDL wrapped in DO blocks with EXCEPTION handlers for idempotency in migration file; init-db.sql uses native IF NOT EXISTS for fresh deployments"
metrics:
  duration_seconds: 306
  completed_date: "2026-04-16"
  tasks_completed: 2
  files_modified: 8
---

# Phase 5 Plan 01: pH Calibration Backend Summary

**One-liner:** pH calibration tracking with overdue alerts — CalibrationStore extended with is_overdue/record_calibration, AlertEngine gains ph_calibration_overdue P1 alert, hourly bridge loop fires/clears alerts, REST API proxies calibration CRUD to bridge.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | DB migration, CalibrationStore extension, AlertEngine ph_calibration_overdue | f49a36a | hub/migrations/05-calibration-and-retention.sql, hub/bridge/calibration.py, hub/bridge/alert_engine.py, hub/init-db.sql |
| 2 | Bridge periodic calibration check, internal HTTP handlers, API calibration router | 2266d2a | hub/bridge/main.py, hub/api/calibration_router.py, hub/api/main.py |

## What Was Built

**DB Migration (`hub/migrations/05-calibration-and-retention.sql`):**
- `ALTER TABLE calibration_offsets ADD COLUMN IF NOT EXISTS last_calibration_date TIMESTAMPTZ` — idempotent for existing deployments
- Hourly `sensor_readings_hourly` continuous aggregate wrapped in DO/EXCEPTION block for idempotency
- Retention policies: 90-day raw, 730-day rollup — each wrapped for idempotency

**init-db.sql updates:**
- `last_calibration_date TIMESTAMPTZ` column added to `calibration_offsets` CREATE TABLE
- `sensor_readings_hourly` cagg DDL and retention policies appended for fresh deployments

**CalibrationStore extension (`hub/bridge/calibration.py`):**
- `TWO_WEEKS = timedelta(weeks=2)` constant
- `_calibration_dates`, `_dry_values`, `_wet_values`, `_temp_coefficients` in-memory caches
- `load_from_db` updated to SELECT all new columns; defensively adds tzinfo if missing
- `is_overdue(zone_id, sensor_type)`: returns True if never calibrated or >14 days ago; uses `datetime.now(timezone.utc)` (never `utcnow()`)
- `record_calibration(...)`: UPSERT with `last_calibration_date = NOW()`, updates all caches
- `get_all_calibrations()`: returns list of dicts with all fields including computed `days_since_calibration`
- `update_calibration_fields(...)`: field-level UPDATE without touching `last_calibration_date`

**AlertEngine extension (`hub/bridge/alert_engine.py`):**
- `"ph_calibration_overdue": ("P1", "pH calibration overdue — {zone_id}", "/zones/{zone_id}")` added to ALERT_DEFINITIONS

**Bridge main.py (`hub/bridge/main.py`):**
- `periodic_calibration_check(db_pool)`: hourly coroutine that queries all ph calibration zones, calls `is_overdue()`, fires/clears `ph_calibration_overdue:{zone_id}` alerts, broadcasts state changes
- `_handle_get_calibrations`: GET /internal/calibrations
- `_handle_record_calibration`: POST /internal/calibrations/{zone_id}/{sensor_type}/record — UPSERT + alert clear
- `_handle_patch_calibration`: PATCH /internal/calibrations/{zone_id}/{sensor_type} — field-level update
- Routes registered in `run_internal_server`; `periodic_calibration_check(db_pool)` added to `asyncio.gather()`

**API calibration router (`hub/api/calibration_router.py`):**
- `CalibrationRecordBody` and `CalibrationPatch` Pydantic models (T-05-01 tamper mitigation)
- GET/POST/PATCH endpoints proxying to bridge; exact error handling pattern from inference_settings_router.py (ClientConnectorError → 503, HTTPException re-raise, generic → 500)

**api/main.py:** calibration_router imported and mounted via `app.include_router(calibration_router)`

## Test Results

135 bridge tests pass (28 new: 9 calibration overdue tests + 5 ph_calibration_overdue alert tests, 14 existing regression).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Boundary test timing drift for is_overdue at exactly 14 days**
- **Found during:** Task 1 GREEN phase — test failed because `datetime.now()` in test and `datetime.now()` in `is_overdue()` are called at different microseconds, making a "14 days ago" date appear slightly more than 14 days by the time `is_overdue` runs
- **Fix:** Test uses `now - timedelta(days=14) + timedelta(seconds=5)` to give a stable "not yet overdue" window. The implementation `> TWO_WEEKS` remains exactly as specified (strict >14 days)
- **Files modified:** hub/bridge/tests/test_calibration.py
- **Commit:** f49a36a

## Known Stubs

None — all data flows are wired. CalibrationStore is loaded from DB in `main()` via `load_from_db`, `record_calibration` writes to DB, `get_all_calibrations` reads from in-memory cache populated from DB.

## Threat Flags

None — all new endpoints follow existing internal network boundary pattern (LAN-only, no external exposure). T-05-01 Pydantic validation applied at API boundary as planned.

## Self-Check: PASSED

### Files exist:
- FOUND: hub/migrations/05-calibration-and-retention.sql
- FOUND: hub/bridge/calibration.py
- FOUND: hub/bridge/alert_engine.py
- FOUND: hub/bridge/main.py
- FOUND: hub/api/calibration_router.py
- FOUND: hub/api/main.py
- FOUND: hub/init-db.sql
- FOUND: .planning/phases/05-operational-hardening/05-01-SUMMARY.md

### Commits exist:
- 8d9a68b: test(05-01): add failing tests (RED)
- f49a36a: feat(05-01): DB migration, CalibrationStore, AlertEngine
- 2266d2a: feat(05-01): bridge loop, internal handlers, API router
