---
phase: 02-actuator-control-alerts-and-dashboard-v1
plan: 03
subsystem: bridge
tags: [python, asyncio, astral, mqtt, fastapi, asyncpg, timescaledb, tdd, pytest]

# Dependency graph
requires:
  - phase: 02-actuator-control-alerts-and-dashboard-v1
    plan: 01
    provides: ZoneConfigStore, actuator_router._send_irrigation_command, active_irrigation_zone
  - phase: 02-actuator-control-alerts-and-dashboard-v1
    plan: 02
    provides: RuleEngine, AlertEngine, compute_health_score, IrrigationLoop

provides:
  - coop_scheduler_loop() astronomical clock scheduler with NOAA sunrise/sunset using astral 3.2
  - _stuck_door_watchdog() fires P0 stuck_door:coop alert via notify_callback after 60s timeout (COOP-03)
  - mark_coop_ack_received() called by bridge to signal watchdog when coop ack arrives
  - GET /api/zones/{zone_id}/history with time-bucketed TimescaleDB queries (30m buckets for 7d, 2h buckets for 30d)
  - POST /api/recommendations/{id}/approve opens irrigation valve via _send_irrigation_command then starts IrrigationLoop
  - POST /api/recommendations/{id}/reject starts backoff window via RuleEngine.reject()
  - Full Phase 2 bridge integration: every sensor reading triggers rule/alert/health evaluation and broadcasts all delta types

affects:
  - 02-04 (dashboard UI consumes recommendation_queue, alert_state, zone_health_score, coop_schedule deltas from integrated bridge)
  - 02-05 (coop UI reads coop_schedule delta broadcast by scheduler)
  - 02-06 (zone health score broadcast by bridge after every sensor write)

# Tech tracking
tech-stack:
  added:
    - astral==3.2 (NOAA astronomical clock — sunrise/sunset calculation from lat/long)
  patterns:
    - Module-level asyncio.Event (_coop_ack_received) for cross-coroutine ack signaling without lock
    - Dependency injection pattern: recommendation_router.init() wires in db_pool at API startup
    - approve_recommendation() calls _send_irrigation_command() before starting IrrigationLoop — valve-open is prerequisite to sensor-feedback loop
    - _read_vwc_high_threshold() reads zone-configured target VWC from DB; falls back to 60.0 — never hardcoded
    - asyncio.gather(bridge_loop, coop_scheduler_loop) runs both coroutines concurrently in bridge main()

key-files:
  created:
    - hub/bridge/coop_scheduler.py
    - hub/bridge/tests/test_coop_scheduler.py
    - hub/api/history_router.py
    - hub/api/recommendation_router.py
  modified:
    - hub/bridge/requirements.txt (added astral==3.2)
    - hub/bridge/main.py (integrated all Phase 2 engines, coop ack handling, asyncio.gather)
    - hub/api/main.py (added history and recommendation routers, DB pool, rec_router_module.init())

key-decisions:
  - "asyncio.Event for stuck-door watchdog — clear() before command publish, wait_for with timeout; if times out, fire alert immediately via notify_callback without going through alert_engine"
  - "approve_recommendation() reads vwc_high_threshold from DB (not hardcoded) — zone's own configured target is the correct irrigation goal"
  - "Coop scheduler uses astral LocationInfo + sun() from env-configured lat/long; open/close offset and hard-close backstop configurable via env vars"

patterns-established:
  - "Watchdog pattern: publish command -> clear event -> wait_for(event, timeout) -> if timeout, fire P0 alert immediately"
  - "Valve-first irrigation approval: open valve (MQTT ack required) before starting IrrigationLoop sensor-feedback — prevents loop monitoring a closed valve"
  - "Time-bucketed history: 30-minute buckets for <=7 days, 2-hour buckets for >7 days — parameterized query prevents SQL injection"

requirements-completed: [COOP-01, COOP-02, COOP-03, COOP-05, COOP-06, COOP-07, ZONE-05, IRRIG-05]

# Metrics
duration: 5min
completed: 2026-04-09
---

# Phase 2 Plan 03: Coop Scheduler, History/Recommendation Endpoints, and Bridge Integration Summary

**Astronomical coop door clock with astral 3.2, P0 stuck-door watchdog, time-bucketed history endpoint, recommendation approve/reject with actual valve open, and full Phase 2 sensor pipeline wired into bridge main loop**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-09T21:49:21Z
- **Completed:** 2026-04-09T21:53:15Z
- **Tasks:** 2
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments

- Coop scheduler calculates daily sunrise/sunset from lat/long using astral 3.2. Open time = sunrise + COOP_OPEN_OFFSET_MINUTES. Close time = min(sunset + COOP_CLOSE_OFFSET_MINUTES, COOP_HARD_CLOSE_HOUR:00 UTC). Runs as asyncio.gather partner alongside bridge_loop.
- Stuck-door watchdog (COOP-03): after publishing a coop command, clears asyncio.Event and calls wait_for with configurable timeout (default 60s). If bridge does not call mark_coop_ack_received() in time, fires P0 alert immediately via notify_callback with stuck_door:coop key.
- GET /api/zones/{zone_id}/history: parameterized TimescaleDB query with time_bucket(), filters BAD quality readings. 30-minute buckets for 7-day queries, 2-hour buckets for 30-day queries.
- approve_recommendation(): reads vwc_high_threshold from DB (not hardcoded), calls _send_irrigation_command() to open valve (MQTT + ack), then starts IrrigationLoop. Raises 502 if valve fails, 409 if another zone is already irrigating.
- Bridge main.py integrates all four Phase 2 engines (RuleEngine, AlertEngine, compute_health_score, IrrigationLoop) into _evaluate_phase2() called after every sensor write. Feed/water percentages computed and broadcast as level deltas.
- All 55 tests pass (4 new coop scheduler tests + 51 pre-existing).

## Task Commits

Each task was committed atomically:

1. **Task 1 RED — Failing coop scheduler tests** - `776db2b` (test)
2. **Task 1 GREEN — Coop scheduler implementation** - `93f5733` (feat)
3. **Task 2 — History endpoint, recommendation endpoints, bridge integration** - `58a5d42` (feat)

## Files Created/Modified

- `hub/bridge/coop_scheduler.py` - NOAA astronomical clock scheduler; get_today_schedule() with offset + hard close backstop; _stuck_door_watchdog() P0 alert on timeout; mark_coop_ack_received() for bridge signal
- `hub/bridge/tests/test_coop_scheduler.py` - 4 tests: sunrise/sunset returns, offset applied, hard close backstop, stuck-door watchdog fires P0 alert with AsyncMock
- `hub/bridge/requirements.txt` - Added astral==3.2
- `hub/api/history_router.py` - GET /api/zones/{zone_id}/history with time_bucket() query; 30m/2h bucket intervals based on days parameter
- `hub/api/recommendation_router.py` - approve/reject endpoints; _read_vwc_high_threshold() from DB; calls _send_irrigation_command() before IrrigationLoop.start()
- `hub/bridge/main.py` - Imports and initializes RuleEngine, AlertEngine, IrrigationLoop, ZoneConfigStore, coop_scheduler; _evaluate_phase2() runs full pipeline per sensor reading; coop ack handling calls mark_coop_ack_received(); asyncio.gather for dual coroutine operation
- `hub/api/main.py` - Includes history_router and recommendation_router; DB pool created at startup; rec_router_module.init() wires db_pool

## Decisions Made

- Used asyncio.Event for stuck-door watchdog — same pattern as pending_acks in actuator_router; lightweight, no external dependencies, sufficient for single-process local system
- approve_recommendation() reads target VWC from DB rather than hardcoding — zone's configured vwc_high_threshold is the semantically correct irrigation target; falls back to 60.0 if DB unavailable
- Valve-open is prerequisite step before starting IrrigationLoop — if MQTT publish or ack fails, return 502 immediately rather than starting a monitoring loop for a potentially-closed valve

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all endpoints and engines are fully implemented. Module-level `_rule_engine = None` variables in recommendation_router.py are dependency injection placeholders populated via `init()` at startup — not stubs.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All Phase 2 backend engines are integrated and operational — dashboard frontend (plans 02-04 through 02-06) can consume all delta types immediately
- Bridge broadcasts: sensor_update, recommendation_queue, alert_state, zone_health_score, feed_level, water_level, coop_schedule, actuator_state
- Coop scheduler runs autonomously; stuck-door alerts fire via the same notify_api channel as all other deltas
- History endpoint ready for frontend chart consumption — requires real sensor data in TimescaleDB (populated by bridge sensor pipeline)

## Self-Check: PASSED

- hub/bridge/coop_scheduler.py: FOUND
- hub/bridge/tests/test_coop_scheduler.py: FOUND
- hub/api/history_router.py: FOUND
- hub/api/recommendation_router.py: FOUND
- Commits 776db2b, 93f5733, 58a5d42: FOUND
- All 55 tests: PASS

---
*Phase: 02-actuator-control-alerts-and-dashboard-v1*
*Completed: 2026-04-09*
