---
phase: 08-milestone-gap-closure
plan: "01"
subsystem: bridge-websocket
tags: [bug-fix, websocket, model-maturity, heartbeat, alerts, ai-07, infra-05, notf-01]
dependency_graph:
  requires: []
  provides: [AI-07, INFRA-05, NOTF-01]
  affects: [hub/api/ws_manager.py, hub/bridge/main.py]
tech_stack:
  added: []
  patterns:
    - periodic coroutine via asyncio.gather() — matches periodic_calibration_check pattern
    - fire-and-forget notify_api() for model_maturity delta broadcast
key_files:
  created: []
  modified:
    - hub/api/ws_manager.py
    - hub/bridge/main.py
decisions:
  - "Import datetime at top of periodic_heartbeat_check() (outside loop) rather than inside loop body — cleaner and avoids repeated sys.modules lookup"
  - "_push_model_maturity() guards against _maturity_tracker is None to handle pre-init calls safely"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-20T19:50:45Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 8 Plan 01: v1.0 Milestone Gap Closure — Summary

**One-liner:** Closed three audit gaps (AI-07 model maturity WebSocket broadcast, INFRA-05 heartbeat watchdog, NOTF-01 node_offline alert) and fixed egg count snapshot field name bug via targeted edits to two files.

## What Was Built

### Task 1: ws_manager.py — egg count field fix and model_maturity support (commit 7f4789b)

Four surgical changes to `hub/api/ws_manager.py`:

1. Added `self._model_maturity: list[dict] = []` to `WebSocketManager.__init__()` after `_feed_consumption`.
2. Added `"model_maturity": self._model_maturity` to the `connect()` snapshot dict — new clients receive current maturity state immediately on connection.
3. Added `elif delta.get("type") == "model_maturity":` branch in `update_state()` that sets `self._model_maturity = delta.get("domains", [])`.
4. Fixed the nesting_box handler: replaced the buggy `"today": delta.get("today", datetime.date.today().isoformat())` (which stored a date string when the bridge sends an integer) with `"estimated_count": delta.get("estimated_count")`. The unused `import datetime` was removed.

### Task 2: main.py — model_maturity push and heartbeat watchdog (commit c013739)

Three targeted additions to `hub/bridge/main.py`:

**`_push_model_maturity()` helper (new function):**
- Async helper that calls `_maturity_tracker.get_all_maturity_states()` and POSTs a `model_maturity` delta to `notify_api()`.
- Guards against `_maturity_tracker is None` (pre-init safety).
- Called in three places: `main()` after startup, `_handle_approve()` after `persist_to_db()`, `_handle_reject()` after `persist_to_db()`.

**`periodic_heartbeat_check(db_pool)` coroutine (new function):**
- Runs every 60 seconds in an infinite loop.
- Queries `node_heartbeats` table for each node's latest heartbeat timestamp.
- Fires `node_offline:{node_id}` alert via `alert_engine.set_alert()` when a node's last heartbeat exceeds 5 minutes ago.
- Clears the alert via `alert_engine.clear_alert()` when the node reconnects.
- Handles edge case: clears `node_offline` alerts for nodes no longer in the heartbeat table.
- Broadcasts updated `alert_state` via `notify_api()` and fires ntfy dispatch whenever alert state changes.
- Added to `asyncio.gather()` — 7 coroutines total.

## Requirements Closed

| Requirement | Status Before | Status After | Evidence |
|-------------|--------------|--------------|----------|
| AI-07 | unsatisfied | satisfied | `_push_model_maturity()` called on startup + approve + reject; `ws_manager.py` snapshot includes `model_maturity` key |
| INFRA-05 | partial | satisfied | `periodic_heartbeat_check()` in `asyncio.gather()`, 5-min threshold, fires/clears `node_offline` alerts |
| NOTF-01 | partial | satisfied | `node_offline` alert now reaches `alert_engine.get_alert_state()` which broadcasts to dashboard and ntfy |

## Bug Fixed

**Egg count snapshot field (`ws_manager.py` line 99):** The `nesting_box` handler stored `delta.get("today", datetime.date.today().isoformat())` — but the bridge sends `estimated_count` (integer), not `today` (string). After a bridge restart, clients connecting before the next nesting_box reading received a date string where an integer was expected. Fixed to `"estimated_count": delta.get("estimated_count")`.

## Deviations from Plan

### Auto-fixed Issues

None — the plan was executed exactly as written with one minor style improvement: moved `from datetime import datetime, timezone, timedelta` to the top of `periodic_heartbeat_check()` (outside the while loop) rather than inside the loop body. The plan noted this was acceptable; the outside-loop placement is slightly cleaner.

## Verification Results

All plan verification checks passed:

```
ws_manager.py: all assertions passed
main.py: all assertions passed (periodic_heartbeat_check appears 3 times: def + 2 gather references)
python -m py_compile hub/api/ws_manager.py  → OK
python -m py_compile hub/bridge/main.py     → OK
grep 'delta.get("today"' hub/api/ws_manager.py  → no matches (bug removed)
model_maturity appears in both files: 4 lines in ws_manager.py, 6 lines in main.py
periodic_heartbeat_check: function def at line 691, gather call at line 1080
```

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | 7f4789b | fix(08-01): correct egg count field and add model_maturity support in ws_manager |
| Task 2 | c013739 | feat(08-01): add model_maturity push and periodic_heartbeat_check to bridge |

## Known Stubs

None — all data paths are wired end-to-end.

## Threat Flags

No new security surface introduced. All changes are internal to the Docker network:
- `notify_api()` posts to `api:8000/internal/notify` — internal only
- `node_heartbeats` data originates from edge nodes, already validated via `HeartbeatPayload` Pydantic model at ingestion
- `model_maturity` data is non-sensitive operational counts (see T-08-02 in threat model)

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| hub/api/ws_manager.py exists | FOUND |
| hub/bridge/main.py exists | FOUND |
| 08-01-SUMMARY.md exists | FOUND |
| commit 7f4789b exists | FOUND |
| commit c013739 exists | FOUND |
