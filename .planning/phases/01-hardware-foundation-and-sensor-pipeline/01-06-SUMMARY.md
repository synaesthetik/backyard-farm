---
phase: 01-hardware-foundation-and-sensor-pipeline
plan: "06"
subsystem: dashboard
tags: [svelte5, sveltekit, websocket, typescript, lucide-svelte, real-time, quality-flags, stale-detection, stuck-detection, node-health]

requires:
  - phase: 01-hardware-foundation-and-sensor-pipeline
    plan: "05"
    provides: "WebSocket endpoint at /ws/dashboard, snapshot-on-connect, sensor_update/heartbeat delta format"

provides:
  - "Live sensor dashboard with ZoneCard components (moisture, pH, temperature per zone)"
  - "Quality flag badges (GOOD/SUSPECT/BAD) inline with each sensor value"
  - "Stale detection: amber border + dimmed values for readings >= 5 minutes old (INFRA-06)"
  - "Stuck sensor indicator: orange row at card bottom when sensor.stuck=true"
  - "SystemHealthPanel: node online/offline status with heartbeat timestamps (UI-07)"
  - "WebSocket reactive store: snapshot-on-connect, delta updates, exponential backoff reconnect"
  - "Responsive layout: 1 column mobile (< 640px), 2 columns desktop (>= 640px)"
  - "WCAG accessibility: aria-live polite on zones, role=status on WS indicator, semantic HTML"

affects: []

tech-stack:
  added: []
  patterns:
    - "Svelte 5 $state runes for Map<zoneId, ZoneState> reactive store"
    - "Map reassignment pattern for reactivity: this.zones = new Map(this.zones.set(...))"
    - "$derived for computed zone-level stale/stuck/latestReceivedAt state"
    - "DashboardStore class as singleton module export (not Svelte store)"
    - "WebSocket exponential backoff: 1s base, 30s max, values NOT cleared on disconnect"

key-files:
  created:
    - hub/dashboard/src/lib/types.ts
    - hub/dashboard/src/lib/ws.svelte.ts
    - hub/dashboard/src/lib/SensorValue.svelte
    - hub/dashboard/src/lib/ZoneCard.svelte
    - hub/dashboard/src/lib/NodeHealthRow.svelte
    - hub/dashboard/src/lib/SystemHealthPanel.svelte
  modified:
    - hub/dashboard/src/routes/+page.svelte

decisions:
  - "DashboardStore as a plain class singleton rather than Svelte writable store — class methods give cleaner WebSocket lifecycle (connect/disconnect) and avoid store subscription boilerplate"
  - "Map reassignment for Svelte 5 reactivity per Research Pitfall 4 — mutation of Map does not trigger reactive updates"
  - "Offline threshold computed in SystemHealthPanel (not WebSocket store) — display concern, not data concern"
  - "Stale detection runs entirely client-side from received_at timestamp per D-16"

metrics:
  duration: ~10min
  completed: 2026-04-07
  tasks_completed: 3
  tasks_total: 3
  files_created: 6
  files_modified: 1
---

# Phase 01 Plan 06: Dashboard Components Summary

**Svelte 5 dashboard with live sensor readings, quality badges, stale/stuck indicators, and node health panel driven by WebSocket reactive store**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-04-07
- **Tasks:** 3/3
- **Files created:** 6
- **Files modified:** 1

## Accomplishments

- TypeScript type system: QualityFlag, SensorReading, ZoneState, NodeState, ConnectionStatus, WSMessage union (DashboardSnapshot | SensorDelta | HeartbeatDelta)
- DashboardStore: Svelte 5 $state runes for zones/nodes Maps, WebSocket connect/disconnect, snapshot-on-connect handler, delta merge, exponential backoff reconnect (1s–30s), values preserved on disconnect per D-16
- Map reassignment pattern applied throughout to satisfy Svelte 5 reactivity (Research Pitfall 4)
- SensorValue: horizontal flex row, 28px/600 tabular-nums value, quality badge pill (GOOD green/SUSPECT amber/BAD red), "--" italic muted on null
- ZoneCard: zone name (truncated at 20 chars), $derived freshness/stale/stuck computed state, STALE amber border + 0.5 opacity dimming, stuck indicator orange row
- NodeHealthRow: 8px status dot (green/red), "Heartbeat Ns ago" / "Last seen Nm ago" copy per UI-SPEC, ONLINE/OFFLINE badge
- SystemHealthPanel: node list with 180s offline threshold, "No nodes connected" empty state
- +page.svelte: sticky 48px header, connection dot with role="status" aria-label, zone grid (1col/2col responsive), aria-live="polite" on zones section, semantic HTML

## Task Commits

1. **Task 1: TypeScript types and WebSocket reactive store** — `ef2c59b`
2. **Task 2: Dashboard components and page layout** — `a4e9356`
3. **Task 3: Visual verification checkpoint** — approved by user (dark theme, Farm Dashboard header, "No zones configured" empty state, "No nodes connected" system health panel all confirmed correct)

## Files Created/Modified

- `hub/dashboard/src/lib/types.ts` — QualityFlag, SensorReading, ZoneState, NodeState, ConnectionStatus, WSMessage types
- `hub/dashboard/src/lib/ws.svelte.ts` — DashboardStore with Svelte 5 $state, WebSocket client, formatElapsed(), isStale()
- `hub/dashboard/src/lib/SensorValue.svelte` — Sensor value row component with quality badge
- `hub/dashboard/src/lib/ZoneCard.svelte` — Zone card with freshness, stale/stuck state
- `hub/dashboard/src/lib/NodeHealthRow.svelte` — Node health row with online/offline status
- `hub/dashboard/src/lib/SystemHealthPanel.svelte` — System health panel container
- `hub/dashboard/src/routes/+page.svelte` — Full dashboard page layout (replaces placeholder)

## Decisions Made

- DashboardStore as a plain class singleton rather than Svelte writable store — class methods give cleaner WebSocket lifecycle (connect/disconnect) and avoid store subscription boilerplate
- Map reassignment for Svelte 5 reactivity per Research Pitfall 4 — mutation of Map does not trigger reactive updates; new Map() assignment is required
- Offline threshold (180s) computed in SystemHealthPanel at render time — display concern that does not belong in the data store
- Stale detection runs entirely client-side from received_at timestamp per D-16 — no server-side stale flag needed

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components are fully wired. Sensor values render from live WebSocket data; empty states ("No zones configured", "No nodes connected") are correct behavior when no data has arrived, not placeholder stubs.

## Issues Encountered

None.

## Self-Check: PASSED

- hub/dashboard/src/lib/types.ts: FOUND
- hub/dashboard/src/lib/ws.svelte.ts: FOUND
- hub/dashboard/src/lib/SensorValue.svelte: FOUND
- hub/dashboard/src/lib/ZoneCard.svelte: FOUND
- hub/dashboard/src/lib/NodeHealthRow.svelte: FOUND
- hub/dashboard/src/lib/SystemHealthPanel.svelte: FOUND
- hub/dashboard/src/routes/+page.svelte: FOUND (modified)
- Commit ef2c59b: FOUND
- Commit a4e9356: FOUND
- npm run build: PASSED (exit 0)
