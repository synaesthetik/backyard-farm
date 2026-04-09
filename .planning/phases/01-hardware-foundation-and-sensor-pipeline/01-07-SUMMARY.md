---
phase: 01-hardware-foundation-and-sensor-pipeline
plan: 07
subsystem: infra
tags: [caddy, websocket, svelte, fastapi, reverse-proxy]

# Dependency graph
requires:
  - phase: 01-hardware-foundation-and-sensor-pipeline
    provides: FastAPI ws_manager at api:8000/ws/dashboard broadcasting live sensor data
provides:
  - Caddy reverse proxy routes /ws/dashboard to FastAPI api:8000
  - server.js serves SvelteKit HTTP only (no WebSocket stub)
  - Browser clients now receive real sensor data via ws_manager.py
affects:
  - dashboard
  - websocket
  - sensor-pipeline

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All WebSocket traffic routed through Caddy to FastAPI — dashboard:3000 handles HTTP only"

key-files:
  created: []
  modified:
    - hub/Caddyfile
    - hub/dashboard/server.js

key-decisions:
  - "Route /ws/dashboard to api:8000 (FastAPI) not dashboard:3000 (SvelteKit) — FastAPI ws_manager.py holds the authoritative live sensor state"
  - "Strip WebSocketServer stub from server.js entirely — dead code now that Caddy no longer routes WS to dashboard:3000"

patterns-established:
  - "Caddy owns all routing decisions — SvelteKit server.js is HTTP-only"

requirements-completed:
  - INFRA-05
  - INFRA-06
  - INFRA-07
  - ZONE-04
  - UI-07

# Metrics
duration: 1min
completed: 2026-04-09
---

# Phase 01 Plan 07: WebSocket Routing Fix Summary

**Caddy /ws/dashboard rerouted from SvelteKit stub (empty snapshot) to FastAPI ws_manager (live sensor data), unblocking all 5 real-time dashboard verification truths**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-09T16:18:12Z
- **Completed:** 2026-04-09T16:18:34Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Fixed single-line Caddyfile routing mismatch that caused all WebSocket data to come from a stub returning `{zones:{}, nodes:{}}`
- Removed WebSocketServer import, wss instance, upgrade handler, and connection handler from server.js
- server.js now serves only SvelteKit HTTP traffic via the built-in `handler` — no WebSocket involvement
- Browser clients connecting to `/ws/dashboard` now reach `ws_manager.py` which sends a real snapshot on connect and broadcasts live sensor deltas

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Caddyfile WebSocket routing and strip server.js WebSocket stub** - `54110bf` (fix)

## Files Created/Modified

- `hub/Caddyfile` - Changed `/ws/dashboard` reverse_proxy target from `dashboard:3000` to `api:8000`
- `hub/dashboard/server.js` - Removed all WebSocket handling; now a minimal HTTP-only SvelteKit server

## Decisions Made

- Route `/ws/dashboard` to `api:8000`: FastAPI ws_manager.py is the authoritative WebSocket handler with real sensor state. The server.js stub was dead code introduced before the routing was wired correctly.
- Strip WebSocketServer from server.js entirely: With Caddy no longer routing WS to dashboard:3000, the upgrade handler and wss instance are unreachable dead code. Leaving them in would be misleading.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - the plan's goal was specifically to remove the stub (`{zones:{}, nodes:{}}`) by correcting the routing to the real ws_manager.

## Next Phase Readiness

- WebSocket data path is now complete: edge daemon -> bridge -> MQTT -> API -> ws_manager -> Caddy -> browser
- The 5 verification truths that depended on real WS data (live sensor readings, freshness timestamps, quality flags, stuck sensor indicator, node health) are now unblocked
- No blockers introduced

---
*Phase: 01-hardware-foundation-and-sensor-pipeline*
*Completed: 2026-04-09*
