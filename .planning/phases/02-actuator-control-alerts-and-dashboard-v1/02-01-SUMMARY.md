---
phase: 02-actuator-control-alerts-and-dashboard-v1
plan: 01
subsystem: api
tags: [fastapi, aiomqtt, pydantic, typescript, websocket, mqtt, asyncio]

# Dependency graph
requires:
  - phase: 01-hardware-foundation-and-sensor-pipeline
    provides: hub/bridge/models.py base models, hub/api/ws_manager.py, hub/bridge/main.py bridge loop, MQTT topic schema

provides:
  - ActuatorCommand, ActuatorAck, RecommendationModel, AlertModel Pydantic models in hub/bridge/models.py
  - ZoneConfigStore and ZoneConfig with env-var defaults in hub/bridge/zone_config.py
  - NotifyPayload extended with 19 Phase 2 optional fields in hub/api/models.py
  - All Phase 2 TypeScript types in hub/dashboard/src/lib/types.ts (AlertEntry, Recommendation, ActuatorStateDelta, ZoneHealthScoreDelta, FeedLevelDelta, WaterLevelDelta, CoopScheduleDelta, extended DashboardSnapshot, expanded WSMessage union)
  - POST /api/actuators/irrigate endpoint with MQTT publish and asyncio.Event ack resolution
  - POST /api/actuators/coop-door endpoint
  - Single-zone-at-a-time 409 invariant (IRRIG-02) enforced in-process
  - 10s ack timeout returning 504 (IRRIG-01)
  - bridge subscribes to farm/+/ack/# and forwards actuator_ack deltas to API
  - WebSocketManager extended with Phase 2 state cache and handlers for all delta types
  - docs/mqtt-topic-schema.md updated with full command/ack specification

affects:
  - 02-02 (alert engine reads ZoneConfigStore thresholds)
  - 02-03 (recommendation engine uses RecommendationModel)
  - 02-04 (dashboard UI consumes ActuatorStateDelta, AlertEntry, Recommendation types)
  - 02-05 (coop schedule uses CoopScheduleDelta type)
  - 02-06 (health score uses ZoneHealthScoreDelta type)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - asyncio.Event for request/response correlation over MQTT (command_id as correlation key)
    - in-process module-level state for single-zone invariant and pending_acks dict
    - Bridge forwards ack through /internal/notify; API routes actuator_ack type to resolve_ack() rather than WebSocket broadcast
    - ZoneConfigStore falls back to env-var defaults when no DB row exists for a zone

key-files:
  created:
    - hub/bridge/zone_config.py
    - hub/api/actuator_router.py
  modified:
    - hub/bridge/models.py
    - hub/api/models.py
    - hub/dashboard/src/lib/types.ts
    - docs/mqtt-topic-schema.md
    - hub/api/main.py
    - hub/api/ws_manager.py
    - hub/bridge/main.py

key-decisions:
  - "asyncio.Event used for ack correlation — single-process model sufficient for single-user LAN system; no Redis/external broker needed"
  - "In-memory active_irrigation_zone variable enforces single-zone invariant — acceptable because API is single-process; resets on restart (acceptable for local system)"
  - "actuator_ack delta NOT broadcast to WebSocket clients — resolve_ack() fires Event, actual state change broadcast handled by actuator_state delta from engine (downstream plan)"

patterns-established:
  - "Command/ack pattern: POST -> MQTT publish -> asyncio.Event wait -> ack via /internal/notify -> resolve_ack() -> return response"
  - "ZoneConfigStore.get() always returns a ZoneConfig (never None) — callers don't need null checks"
  - "NotifyPayload is the single internal delta type — all bridge-to-API communication goes through /internal/notify"

requirements-completed: [IRRIG-01, IRRIG-02]

# Metrics
duration: 4min
completed: 2026-04-10
---

# Phase 2 Plan 01: Irrigation Command Routing and Data Contracts Summary

**MQTT command/ack flow with asyncio.Event correlation, single-zone 409 invariant, and all Phase 2 Pydantic/TypeScript contracts established as a foundation for the remaining 5 plans**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-10T03:04:27Z
- **Completed:** 2026-04-10T03:08:05Z
- **Tasks:** 2
- **Files modified:** 7 (5 modified, 2 created)

## Accomplishments

- All Phase 2 Pydantic models (ActuatorCommand, ActuatorAck, RecommendationModel, AlertModel) added to hub/bridge/models.py
- ZoneConfigStore created with env-var defaults and async DB load — downstream alert and recommendation plans can call `store.get(zone_id)` without null checks
- POST /api/actuators/irrigate and POST /api/actuators/coop-door endpoints with full MQTT command/ack lifecycle: publish -> asyncio.Event wait -> 10s timeout -> 504 or confirmed response
- Single-zone-at-a-time invariant (IRRIG-02) enforced: second open while zone active returns 409
- Bridge now subscribes to farm/+/ack/# and forwards parsed ack payloads to /internal/notify as actuator_ack deltas; API routes them to resolve_ack() bypassing WebSocket broadcast
- WebSocketManager extended: 7 Phase 2 state fields, extended snapshot on connect, update_state handlers for all delta types
- TypeScript WSMessage union expanded from 3 to 10 types; DashboardSnapshot extended with Phase 2 fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Data contracts — Pydantic models, TypeScript types, zone config, MQTT schema** - `6f3b562` (feat)
2. **Task 2: Actuator command endpoints and ack flow with single-zone invariant** - `0f3522d` (feat)

## Files Created/Modified

- `hub/bridge/models.py` - Added ActuatorCommand, ActuatorAck, RecommendationModel, AlertModel; added Optional and timezone imports
- `hub/bridge/zone_config.py` - New: ZoneConfigStore with async DB load and env-var defaults; ZoneConfig dataclass
- `hub/api/models.py` - Extended NotifyPayload with 19 Phase 2 optional fields (command_id, action, alerts, recommendations, etc.)
- `hub/dashboard/src/lib/types.ts` - Added 9 Phase 2 interfaces; extended DashboardSnapshot; expanded WSMessage union to 10 types
- `docs/mqtt-topic-schema.md` - Replaced reserved topics stub with full command/ack payload specification and delivery contract
- `hub/api/actuator_router.py` - New: POST /api/actuators/irrigate and POST /api/actuators/coop-door with MQTT publish, asyncio.Event ack, 409/502/504 error handling
- `hub/api/main.py` - Added actuator_router include; updated internal_notify to route actuator_ack to resolve_ack()
- `hub/api/ws_manager.py` - Added Phase 2 state fields; extended snapshot; added 7 delta type handlers in update_state()
- `hub/bridge/main.py` - Added farm/+/ack/# subscription; added /ack/ topic handler producing actuator_ack delta

## Decisions Made

- Used asyncio.Event for ack correlation — no external broker needed for single-user LAN system; pending_acks dict keyed by command_id (UUID v4)
- In-memory active_irrigation_zone enforces single-zone invariant — acceptable for single-process API; resets on restart (intentional for local system)
- actuator_ack NOT broadcast to WebSocket — only fires the asyncio.Event; actual actuator_state delta will be broadcast by the alert/state engine in a downstream plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

asyncpg not installed in local Python environment (bridge runs in Docker) — verified bridge models and zone_config via ast.parse() and class name inspection rather than runtime import. All verification passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All data contracts are defined and importable — plans 02-02 through 02-06 can import ZoneConfigStore, AlertModel, RecommendationModel, and all TypeScript types directly
- Actuator endpoints are wired but will return 504 until real edge nodes ack — acceptable for dev environment with mock acks
- WebSocketManager snapshot now includes Phase 2 fields; dashboard UI plans can consume them without further API changes

---
*Phase: 02-actuator-control-alerts-and-dashboard-v1*
*Completed: 2026-04-10*
