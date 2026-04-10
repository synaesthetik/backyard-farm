---
phase: 03-flock-management-and-unified-dashboard
plan: 06
subsystem: api
tags: [fastapi, asyncpg, websocket, flock, egg-estimation, production-model, timescaledb, python]

dependency_graph:
  requires:
    - 03-01 (flock_config.FlockConfig, egg_estimator, production_model bridge modules)
  provides:
    - GET /api/flock/config — current flock configuration from DB or defaults
    - PUT /api/flock/config — validated upsert of flock configuration
    - GET /api/flock/egg-history — actual vs expected daily egg counts for charting
    - POST /api/flock/refresh-eggs — immediate estimation from latest nesting box reading
    - WebSocket snapshot egg_count field (hen_present, raw_weight_grams, today, updated_at)
    - WebSocket snapshot feed_consumption field (rate_grams_per_day, weekly)
  affects:
    - 03-03 (ProductionChart reads egg-history endpoint)
    - 03-04 (FlockSettings reads/writes /api/flock/config; tare button calls refresh-eggs)
    - 03-05 (CoopPanel reads egg_count from WebSocket snapshot)

tech-stack:
  added: []
  patterns:
    - APIRouter per domain (flock_router.py mirrors actuator_router.py structure)
    - Inline production model in API layer — avoids bridge container coupling
    - Parameterized asyncpg queries ($1 placeholders) throughout for SQL injection prevention
    - Single-row config table pattern (DELETE + INSERT upsert for flock_config)
    - WebSocket snapshot cache extended with Phase 3 delta type handlers

key-files:
  created:
    - hub/api/flock_router.py
  modified:
    - hub/api/main.py
    - hub/api/models.py
    - hub/api/ws_manager.py

key-decisions:
  - "Production model inlined in flock_router.py rather than imported from bridge — avoids cross-container Python package dependency at runtime"
  - "Upsert strategy for flock_config uses DELETE+INSERT (single config row) rather than ON CONFLICT — simpler for a singleton config table"
  - "egg-history endpoint computes expected_count on-the-fly per date using per-day daylight factor — accurate but slightly slower; acceptable for 30-90 day max range"
  - "refresh-eggs queries sensor_readings filtered by zone_id='coop' and sensor_type='nesting_box_weight' — mirrors bridge ingestion pattern"

requirements-completed:
  - FLOCK-03
  - FLOCK-05

duration: ~15 minutes
completed: "2026-04-09"
---

# Phase 3 Plan 06: Flock REST API and WebSocket Snapshot Summary

**FastAPI flock router with 4 endpoints (config CRUD, 30-day egg history, immediate refresh-eggs) and WebSocket snapshot extended with egg_count and feed_consumption state for new connections.**

## Performance

- **Duration:** ~15 minutes
- **Tasks:** 1
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Created `hub/api/flock_router.py` with all four required endpoints mounted at `/api/flock`
- PUT /config validates flock_size >= 1, egg_weight_grams > 0, hen_weight_threshold_grams > 0 — returns 422 with detail message on invalid input
- GET /egg-history returns per-day `{date, actual_count, expected_count}` array; expected_count computed inline using the same piecewise production model as the bridge
- POST /refresh-eggs reads latest `nesting_box_weight` from `sensor_readings`, estimates eggs, upserts `egg_counts`, returns 404 if no reading exists
- Extended `NotifyPayload` in `models.py` with Phase 3 fields: `estimated_count`, `hen_present`, `raw_weight_grams`, `rate_grams_per_day`, `weekly`
- Extended `WebSocketManager` snapshot with `egg_count` and `feed_consumption` (both initialized to `null`); `nesting_box` delta updates `egg_count` cache, `feed_consumption` delta updates `feed_consumption` cache

## Task Commits

1. **Task 1: Flock API router, model extensions, and WebSocket snapshot** — `ea0556e` (feat)

## Files Created/Modified

- `hub/api/flock_router.py` — New APIRouter with GET/PUT /config, GET /egg-history, POST /refresh-eggs; inline production model helpers; parameterized asyncpg queries
- `hub/api/main.py` — Added `import flock_router` and `app.include_router(flock_router.router)`
- `hub/api/models.py` — Added `estimated_count`, `hen_present`, `raw_weight_grams`, `rate_grams_per_day`, `weekly` to `NotifyPayload`
- `hub/api/ws_manager.py` — Added `_egg_count` and `_feed_consumption` snapshot fields; added `nesting_box` and `feed_consumption` delta handlers in `update_state()`

## Decisions Made

- **Production model inlined:** The bridge container runs a separate Python process; importing from `hub/bridge/` at API container runtime would require sharing Python packages across containers. Instead, the production model arithmetic is duplicated inline in `flock_router.py`. It is pure computation (no I/O), so duplication is low-risk and correct.
- **Upsert via DELETE + INSERT:** The `flock_config` table holds a single configuration row. Rather than using `ON CONFLICT` (which requires a unique constraint to already exist and be named), DELETE + INSERT is simpler and equally correct for a singleton config table.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All endpoints are fully implemented with real DB queries and production model computation.

## Self-Check

### Files exist:
- hub/api/flock_router.py — FOUND
- hub/api/main.py — FOUND (modified)
- hub/api/models.py — FOUND (modified)
- hub/api/ws_manager.py — FOUND (modified)

### Commits exist:
- ea0556e — Task 1

## Self-Check: PASSED

## Next Phase Readiness

- `/api/flock/config` is ready for Plan 03-04 (FlockSettings page)
- `/api/flock/egg-history` is ready for Plan 03-03 (ProductionChart)
- `/api/flock/refresh-eggs` is ready for Plan 03-04 (manual refresh button)
- WebSocket snapshot `egg_count` and `feed_consumption` fields are ready for Plan 03-05 (CoopPanel)

---
*Phase: 03-flock-management-and-unified-dashboard*
*Completed: 2026-04-09*
