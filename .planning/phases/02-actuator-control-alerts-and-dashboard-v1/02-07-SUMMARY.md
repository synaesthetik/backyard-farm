---
phase: 02-actuator-control-alerts-and-dashboard-v1
plan: "07"
subsystem: bridge-api-ipc
tags: [bridge, api, aiohttp, recommendation, ipc, gap-closure]
dependency_graph:
  requires: [02-02, 02-03]
  provides: [approve-reject-functional]
  affects: [recommendation-queue-ui]
tech_stack:
  added: [aiohttp-server-in-bridge, aiohttp-client-in-api]
  patterns: [internal-http-ipc, reverse-proxy-between-docker-services, expose-not-ports]
key_files:
  created: []
  modified:
    - hub/bridge/main.py
    - hub/api/recommendation_router.py
    - hub/api/requirements.txt
    - hub/docker-compose.yml
decisions:
  - "Bridge serves internal HTTP on 8001 via aiohttp.web (Option A from verification gaps — minimal, no new infrastructure)"
  - "API proxies approve/reject to bridge via aiohttp.ClientSession; init() signature kept identical so api/main.py requires no changes"
  - "docker-compose uses expose: not ports: for 8001 — internal Docker network reachability only, not host-bound"
  - "Approve rollback: if MQTT publish fails, bridge calls rule_engine.reject() so recommendation is not stuck approved-but-unexecuted"
metrics:
  duration_minutes: 25
  completed: "2026-04-10T18:45:42Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
  commits: 2
---

# Phase 02 Plan 07: Bridge Internal HTTP Server and API Proxy — Summary

**One-liner:** Bridge exposes aiohttp HTTP server on port 8001 with approve/reject handlers; API recommendation_router proxies to bridge instead of calling always-None local rule_engine, eliminating the 503 dead-end.

## What Was Built

This plan closes the cross-process boundary gap identified in 02-VERIFICATION.md. The API and bridge run as separate Docker containers. `RuleEngine` and `IrrigationLoop` live only in the bridge — the API's `recommendation_router.init()` correctly receives `rule_engine=None` because those instances are unreachable from the API process, causing every approve/reject call to return HTTP 503.

**Fix:** Add a minimal internal HTTP server (aiohttp, port 8001) to the bridge, and replace the API's direct rule_engine calls with HTTP proxy calls to that server. This mirrors the existing `notify_api()` pattern (bridge → API) but adds the reverse direction (API → bridge).

### Task 1: Bridge internal HTTP server (hub/bridge/main.py)

- `from aiohttp import web` added at top-level (aiohttp already present in bridge requirements via aiomqtt)
- `_bridge_read_vwc_high_threshold(zone_id, db_pool)` — reads `vwc_high_threshold` from `zone_configs` table, falls back to 60.0
- `_handle_approve(request)` — calls `rule_engine.approve()`, publishes MQTT valve-open command via `aiomqtt.Client`, calls `irrigation_loop.start(zone_id, target_vwc)`, broadcasts `recommendation_queue` delta via `notify_api()`. On MQTT failure: calls `rule_engine.reject()` to undo the approve state before returning 502.
- `_handle_reject(request)` — calls `rule_engine.reject()`, broadcasts `recommendation_queue` delta
- `run_internal_server(db_pool)` — binds `aiohttp.web.Application` to `0.0.0.0:8001`, registers both routes, runs `asyncio.Event().wait()` to keep alive alongside other coroutines
- `main()` updated: `run_internal_server(db_pool)` added to `asyncio.gather()`

### Task 2: API proxy and docker-compose wiring (hub/api/recommendation_router.py, hub/docker-compose.yml)

- `recommendation_router.py` rewritten: `approve_recommendation()` and `reject_recommendation()` now proxy to `http://bridge:8001/internal/recommendations/{id}/approve|reject` via `aiohttp.ClientSession`
- `init()` signature preserved — `hub/api/main.py` requires zero changes
- `_rule_engine` / `_irrigation_loop` accepted but unused (bridge owns them); `_notify_callback`, `_ws_manager`, `_db_pool` retained for future use
- `BRIDGE_INTERNAL_URL` env var (default `http://bridge:8001`) makes the bridge URL configurable
- `aiohttp==3.11.16` added to `hub/api/requirements.txt`
- `hub/docker-compose.yml`: `bridge` service gains `expose: ["8001"]` (Docker-internal only, not host-bound)
- `hub/docker-compose.yml`: `api` service `depends_on` gains `bridge` so API starts after bridge's internal server is up

## End-to-End Flow After This Plan

```
Dashboard → POST /api/recommendations/{id}/approve
  → API recommendation_router (aiohttp.ClientSession)
    → POST http://bridge:8001/internal/recommendations/{id}/approve
      → bridge rule_engine.approve(rec_id)          # returns zone_id
      → bridge _bridge_read_vwc_high_threshold()     # reads target VWC from DB
      → aiomqtt.Client.publish(farm/{zone_id}/commands/irrigate)  # opens valve
      → irrigation_loop.start(zone_id, target_vwc)  # starts sensor-feedback loop
      → notify_api(recommendation_queue delta)       # removes card from dashboard
      ← 200 {"status": "approved", "zone_id": ..., "target_vwc": ...}
  ← 200 (forwarded to dashboard)
```

## Verification Results

| Check | Result |
|-------|--------|
| `python3 -c "import ast; ast.parse(open('hub/bridge/main.py').read())"` | OK |
| `python3 -c "import ast; ast.parse(open('hub/api/recommendation_router.py').read())"` | OK |
| `grep -q "_handle_approve" hub/bridge/main.py` | OK |
| `grep -q "_handle_reject" hub/bridge/main.py` | OK |
| `grep -q "run_internal_server" hub/bridge/main.py` | OK |
| `grep -c "8001" hub/bridge/main.py` | 4 occurrences |
| `grep -q "BRIDGE_INTERNAL_URL" hub/api/recommendation_router.py` | OK |
| `grep -q "aiohttp.ClientSession" hub/api/recommendation_router.py` | OK |
| `grep -q "if not _rule_engine" hub/api/recommendation_router.py` | Not present (removed) |
| `grep -q "expose" hub/docker-compose.yml` | OK |
| `grep -q "8001" hub/docker-compose.yml` | OK |
| api.depends_on includes bridge | OK |
| Bridge pytest (55 tests) | 55 passed |
| Dashboard npm test (45 tests) | 45 passed |

## Requirements Satisfied

| Requirement | Was | Now |
|-------------|-----|-----|
| AI-01 | PARTIAL (queue displays; approve/reject 503) | SATISFIED |
| AI-02 | VERIFIED | VERIFIED (unchanged) |
| AI-04 | VERIFIED | VERIFIED (unchanged) |
| AI-05 | PARTIAL (back-off logic correct; reject 503) | SATISFIED |
| IRRIG-05 | PARTIAL (IrrigationLoop exists; approve 503) | SATISFIED |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All wiring is complete. The approve handler connects to real `rule_engine`, real `irrigation_loop`, and real MQTT. The reject handler connects to real `rule_engine`. No placeholder or hardcoded values in the critical path.

## Self-Check

### Created files exist
- `.planning/phases/02-actuator-control-alerts-and-dashboard-v1/02-07-SUMMARY.md` — this file

### Commits exist
- `bc5a576` — feat(02-07): add internal HTTP server to bridge for approve/reject handlers
- `bf30645` — feat(02-07): wire API recommendation_router to proxy to bridge and expose port 8001

## Self-Check: PASSED
