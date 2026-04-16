---
phase: 05-operational-hardening
plan: 02
subsystem: bridge-notifications, api-storage
tags: [ntfy, push-notifications, storage, purge, timescaledb, sidecar]
dependency_graph:
  requires: [05-01]
  provides: [ntfy-settings-sidecar, ntfy-dispatch, ntfy-api-router, storage-api-router]
  affects: [hub/bridge/main.py, hub/api/main.py]
tech_stack:
  added: [ntfy (self-hosted push server, external)]
  patterns: [JSON sidecar persistence, aiohttp proxy router, asyncio.create_task fire-and-forget]
key_files:
  created:
    - hub/bridge/ntfy_settings.py
    - hub/bridge/ntfy.py
    - hub/bridge/tests/test_ntfy_settings.py
    - hub/bridge/tests/test_ntfy.py
    - hub/api/ntfy_router.py
    - hub/api/storage_router.py
  modified:
    - hub/bridge/main.py
    - hub/api/main.py
decisions:
  - NtfySettings mirrors AISettings thread-safe JSON sidecar pattern exactly
  - ntfy dispatch uses asyncio.create_task() at all call sites to avoid blocking bridge main loop
  - storage_router queries TimescaleDB directly (not bridged) since API has its own DB pool
  - purge uses drop_chunks with 90-day INTERVAL — cannot delete recent data by design
metrics:
  duration_minutes: 18
  completed_date: "2026-04-16"
  tasks_completed: 2
  files_created: 6
  files_modified: 2
  tests_added: 9
  tests_passing: 144
---

# Phase 5 Plan 02: ntfy Push Notifications and Storage API Summary

**One-liner:** ntfy push notification backend (NtfySettings JSON sidecar + aiohttp dispatch) wired into all bridge alert paths, plus storage stats/purge REST endpoints using TimescaleDB pg_total_relation_size and drop_chunks.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | NtfySettings sidecar, ntfy dispatch, bridge integration | 7ab2cdf | ntfy_settings.py, ntfy.py, main.py (bridge) |
| 2 | ntfy API router, storage API router, api/main.py mount | dea3bf4 | ntfy_router.py, storage_router.py, main.py (api) |

## What Was Built

**Task 1 — Bridge layer:**

- `hub/bridge/ntfy_settings.py`: `NtfySettings` class with threading.Lock, JSON sidecar persistence, env-var seeding (NTFY_URL, NTFY_TOPIC), and `is_enabled()` guard (False when URL empty or enabled=False).
- `hub/bridge/ntfy.py`: `send_ntfy_notification()` (fire-and-forget, 5s timeout, P0→priority 5, P1→priority 3) and `send_ntfy_test()` for the test endpoint.
- `hub/bridge/main.py`: module-level `ntfy_settings = NtfySettings()`, `_dispatch_ntfy_for_alerts()` helper, `asyncio.create_task(_dispatch_ntfy_for_alerts())` injected into all four alert-change paths (`_evaluate_phase2`, `periodic_flock_loop`, `daily_feed_loop`, `periodic_calibration_check`), and three internal HTTP handlers (`GET/PATCH /internal/ntfy-settings`, `POST /internal/ntfy-test`) registered in `run_internal_server`.
- 9 tests in `test_ntfy_settings.py` and `test_ntfy.py` — all passing.

**Task 2 — API layer:**

- `hub/api/ntfy_router.py`: `NtfySettingsPatch` Pydantic model, `GET/PATCH /api/settings/notifications`, `POST /api/settings/notifications/test` — all proxy to bridge internal server with standard error handling (503 bridge unreachable, 500 unexpected).
- `hub/api/storage_router.py`: `GET /api/storage/stats` (pg_total_relation_size per-table + timescaledb_information.jobs retention policies, human-readable total), `POST /api/storage/purge` (drop_chunks INTERVAL '90 days').
- `hub/api/main.py`: imports and mounts both new routers.

## Decisions Made

- **NtfySettings mirrors AISettings**: Same threading.Lock + JSON sidecar pattern already proven in Phase 4 — no deviation needed.
- **asyncio.create_task at call sites**: ntfy dispatch is non-blocking at all four call sites. `_dispatch_ntfy_for_alerts()` itself also checks `is_enabled()` as a double guard.
- **storage_router queries DB directly**: API process has its own asyncpg pool via `get_db_pool()` — no bridge proxy needed for read-only storage queries or purge.
- **drop_chunks 90-day INTERVAL**: Chosen to match standard data retention; only drops full chunks older than 90 days, protecting recent data (T-05-07).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all endpoints are fully wired. Storage stats and ntfy settings both return live data from TimescaleDB and bridge respectively.

## Threat Flags

No new threat surface beyond what was documented in the plan's threat model (T-05-04 through T-05-08).

## Self-Check: PASSED

Files verified:
- hub/bridge/ntfy_settings.py — exists, contains NtfySettings class
- hub/bridge/ntfy.py — exists, contains send_ntfy_notification and send_ntfy_test
- hub/bridge/main.py — contains ntfy_settings import, _dispatch_ntfy_for_alerts, route registrations
- hub/api/ntfy_router.py — exists, contains NtfySettingsPatch and all three endpoints
- hub/api/storage_router.py — exists, contains pg_total_relation_size and drop_chunks
- hub/api/main.py — contains ntfy_router and storage_router includes
- Commits 7ab2cdf and dea3bf4 exist in git log
- 144 bridge tests passing (no regressions)
