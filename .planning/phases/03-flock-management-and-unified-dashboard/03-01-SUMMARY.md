---
phase: 03-flock-management-and-unified-dashboard
plan: 01
subsystem: bridge
tags: [flock, egg-estimation, production-model, feed-consumption, alert-engine, timescaledb, python, tdd]
dependency_graph:
  requires:
    - 02-actuator-control-alerts-and-dashboard-v1 (alert_engine, bridge pipeline)
  provides:
    - egg_estimator.estimate_egg_count
    - production_model.compute_expected_production
    - production_model.compute_age_factor
    - production_model.compute_daylight_factor
    - production_model.BREED_LAY_RATES
    - feed_consumption.compute_daily_feed_consumption
    - flock_config.FlockConfig
    - flock_config.FlockConfigStore
    - alert_engine: production_drop + feed_consumption_drop alerts
    - main.py: periodic_flock_loop + daily_feed_loop
  affects:
    - 03-06 (flock API router + WebSocket snapshot extensions consume these modules)
tech_stack:
  added: []
  patterns:
    - TDD: RED test files written first, modules implemented second
    - piecewise linear age factor curve (0-24w ramp, 24-72w plateau, 72w+ decline at 0.15/year, floor 0.2)
    - astral library for daylight hours with UTC midnight-crossing fix (sunset < sunrise detected and corrected)
    - Pitfall 4 guard: skip production/feed alert when fewer than 3 days of data
    - Periodic async loop pattern (asyncio.sleep) added to asyncio.gather() alongside bridge_loop
key_files:
  created:
    - hub/bridge/flock_config.py
    - hub/bridge/egg_estimator.py
    - hub/bridge/production_model.py
    - hub/bridge/feed_consumption.py
    - hub/bridge/tests/test_egg_estimator.py
    - hub/bridge/tests/test_production_model.py
    - hub/bridge/tests/test_feed_consumption.py
  modified:
    - hub/init-db.sql
    - hub/bridge/alert_engine.py
    - hub/bridge/main.py
    - docs/mqtt-topic-schema.md
decisions:
  - "Hen detection uses >= threshold (not >) so exactly-at-threshold weight correctly marks hen present"
  - "astral sunset < sunrise UTC midnight-crossing corrected by adding timedelta(days=1) to sunset"
  - "feed_consumption_drop alert uses clear_above=False (fires when deviation exceeds 30%, clears when below 25%)"
metrics:
  duration: ~30 minutes
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_created: 7
  files_modified: 4
  tests_added: 35
  tests_total: 90
---

# Phase 3 Plan 01: Flock Backend Core Summary

**One-liner:** Nesting box weight-to-egg estimation pipeline with piecewise age/daylight production model, refill-detecting feed consumption, and production/feed drop alerts wired into the bridge periodic loop.

## What Was Built

Task 1 established the data backbone for Phase 3 flock management:

- **`flock_config.py`**: `FlockConfig` dataclass (breed, hatch_date, flock_size, supplemental_lighting, hen_weight_threshold, egg_weight, tare_weight, lat/lon) and `FlockConfigStore` with `load_from_db(pool)` — mirrors the `zone_config.py` pattern exactly.

- **`egg_estimator.py`**: `estimate_egg_count(weight_grams, flock_config) -> (int, bool)` — subtracts tare, detects hen presence (>= threshold), subtracts hen weight from effective egg weight, clamps to zero, returns `(egg_count, hen_present)`.

- **`production_model.py`**: `BREED_LAY_RATES` (13 breeds including Custom=None), `compute_age_factor()` (piecewise linear: 0-24w ramp, 24-72w plateau, 72w+ decline at 0.15/year, floor 0.2), `compute_daylight_factor()` (astral-based, 0/0 fallback to 0.85, supplemental_lighting shortcut to 1.0), `compute_expected_production()` (flock_size × lay_rate × age_factor × daylight_factor).

- **`feed_consumption.py`**: `compute_daily_feed_consumption(start, end) -> (float|None, bool)` — returns `(None, True)` on refill detection (end > start), otherwise `(start - end, False)`.

- **DB schema**: Three new tables appended to `hub/init-db.sql`: `flock_config`, `egg_counts`, `feed_daily_consumption`.

- **MQTT docs**: `farm/coop/sensors/nesting_box_weight` documented in `docs/mqtt-topic-schema.md`.

- **35 unit tests** across 3 test files, all passing.

Task 2 wired everything into the running bridge:

- **`alert_engine.py`**: Added `production_drop` (hysteresis 10.0, P1) and `feed_consumption_drop` (hysteresis 5.0, P1) to both `HYSTERESIS_BANDS` and `ALERT_DEFINITIONS`.

- **`main.py`**: Imports all flock modules; creates module-level `flock_config_store`; loads it in `main()` alongside calibration and zone configs; adds `_evaluate_phase3_nesting_box()` for real-time per-reading nesting box handling; adds `periodic_flock_loop()` (30-min interval — UPSERT egg_counts, production drop alert with <3 day guard); adds `daily_feed_loop()` (midnight UTC — feed delta, 7-day sparkline delta, feed consumption drop alert with <3 day guard); both loops in `asyncio.gather()`.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | e08e73e | feat(03-01): flock data modules, DB schema, and unit tests |
| 2 | a0d0060 | feat(03-01): alert engine extensions and bridge flock integration |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Hen detection threshold uses >= instead of >**
- **Found during:** Task 1, GREEN phase test run
- **Issue:** `test_hen_only_no_eggs` failed because `1500 > 1500` is `False` — the plan behavior states weight exactly at hen threshold should detect hen presence with 0 eggs
- **Fix:** Changed `net_weight > hen_weight_threshold` to `net_weight >= hen_weight_threshold` in `egg_estimator.py`
- **Files modified:** `hub/bridge/egg_estimator.py`
- **Commit:** e08e73e

**2. [Rule 1 - Bug] astral daylight calculation returns negative hours for western longitudes**
- **Found during:** Task 1, GREEN phase test run
- **Issue:** `compute_daylight_factor(lat=40.0, lon=-75.0, date=2026-06-21)` returned -0.53 because astral returns UTC timestamps where summer sunset in UTC-5 falls numerically after midnight UTC (e.g. 00:32 UTC next day), making `sunset < sunrise` arithmetically
- **Fix:** After calling `astral.sun()`, check if `sunset < sunrise`; if so, add `timedelta(days=1)` to sunset before computing difference
- **Files modified:** `hub/bridge/production_model.py`
- **Commit:** e08e73e

## Known Stubs

None. All modules are fully implemented with real logic. No hardcoded empty values or placeholder returns.

## Self-Check: PASSED

Files exist:
- hub/bridge/flock_config.py — FOUND
- hub/bridge/egg_estimator.py — FOUND
- hub/bridge/production_model.py — FOUND
- hub/bridge/feed_consumption.py — FOUND
- hub/bridge/tests/test_egg_estimator.py — FOUND
- hub/bridge/tests/test_production_model.py — FOUND
- hub/bridge/tests/test_feed_consumption.py — FOUND

Commits exist:
- e08e73e — FOUND
- a0d0060 — FOUND

Test results: 90 passed, 0 failed
