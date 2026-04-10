---
phase: 02-actuator-control-alerts-and-dashboard-v1
plan: 04
subsystem: dashboard
tags: [svelte5, sveltekit, typescript, websocket, spa, tabbar, alertbar, pwa]

# Dependency graph
requires:
  - phase: 02-actuator-control-alerts-and-dashboard-v1
    plan: 01
    provides: TypeScript types (AlertEntry, Recommendation, HealthScore, CoopSchedule, all delta types) in hub/dashboard/src/lib/types.ts

provides:
  - DashboardStore extended with 7 Phase 2 state fields and handlers for all 8 delta types in hub/dashboard/src/lib/ws.svelte.ts
  - TabBar.svelte — fixed bottom navigation, 3 tabs (Zones/Coop/Recs), active underline, aria-label="Main navigation"
  - AlertBar.svelte — persistent P0/P1 alert bar with role="alert", deep-link goto(), grouped count badge
  - Toast.svelte — fixed-position error toast with 5s auto-dismiss, aria-live="assertive"
  - CommandButton.svelte — spinner + disabled actuator command wrapper with aria-disabled and aria-busy
  - HealthBadge.svelte — GOOD/WARN/CRIT pill badge with aria-label, color-coded per health score
  - Multi-route SPA shell: /coop, /zones/[id], /recommendations route stubs
  - +layout.svelte rewritten — WebSocket lifecycle, header, AlertBar, TabBar, Toast
  - ZoneCard extended — tappable (goto + role=button + onkeydown), HealthBadge in header row

affects:
  - 02-05 (coop route stub and zone detail stub are the scaffolds it fills in)
  - 02-06 (recommendations route stub filled in by plan 02-06)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - farm:toast CustomEvent on window — layout listens for it; any component dispatches it without prop drilling
    - $derived($page.params.id) for zone ID extraction in dynamic route
    - WebSocket lifecycle owned by +layout.svelte (onMount/onDestroy) — single connect/disconnect for all routes

key-files:
  created:
    - hub/dashboard/src/lib/TabBar.svelte
    - hub/dashboard/src/lib/AlertBar.svelte
    - hub/dashboard/src/lib/Toast.svelte
    - hub/dashboard/src/lib/CommandButton.svelte
    - hub/dashboard/src/lib/HealthBadge.svelte
    - hub/dashboard/src/routes/coop/+page.svelte
    - hub/dashboard/src/routes/zones/[id]/+page.svelte
    - hub/dashboard/src/routes/recommendations/+page.svelte
  modified:
    - hub/dashboard/src/lib/ws.svelte.ts
    - hub/dashboard/src/lib/ZoneCard.svelte
    - hub/dashboard/src/routes/+layout.svelte
    - hub/dashboard/src/routes/+page.svelte

key-decisions:
  - "Toast dispatched via window CustomEvent (farm:toast) — avoids prop drilling through all feature pages; layout owns the Toast component and handles dismissal"
  - "WebSocket lifecycle in +layout.svelte (not +page.svelte) — single connect/disconnect across all route navigations; prevents reconnect thrashing on tab switching"
  - "Route stubs contain intentional placeholder text — they will be replaced by plans 02-05 and 02-06; this is by design per the plan output spec"

# Metrics
duration: 8min
completed: 2026-04-10
---

# Phase 2 Plan 04: Frontend Foundation — Routing, Layout, Shared Components, and WebSocket Extension Summary

**Multi-route SPA shell with bottom tab navigation, persistent alert bar, 5 shared Phase 2 components, and WebSocket store extended for all Phase 2 delta types — the app scaffold that plans 02-05 and 02-06 build upon**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-10T17:01:00Z
- **Completed:** 2026-04-10T17:09:54Z
- **Tasks:** 2
- **Files modified:** 12 (8 created, 4 modified)

## Accomplishments

- DashboardStore extended with 7 Phase 2 reactive state properties (`alerts`, `recommendations`, `actuatorStates`, `zoneHealthScores`, `feedLevel`, `waterLevel`, `coopSchedule`). Snapshot handler populates all fields from the initial connect payload. Delta handlers added for all 8 Phase 2 message types (`alert_state`, `recommendation_queue`, `actuator_state`, `zone_health_score`, `feed_level`, `water_level`, `coop_schedule`).
- TabBar: fixed bottom nav bar (56px + safe-area-inset-bottom), 3 tabs with Lucide icons, accent underline on active tab, `aria-label="Main navigation"`, `aria-current="page"` on active tab, `<a>` links for SvelteKit routing (no JS navigation).
- AlertBar: persistent P0/P1 alert rows rendered from `dashboardStore.alerts`. `role="alert"` on container, `aria-live="assertive"` for P0 / `aria-live="polite"` for P1. Tappable rows call `goto(alert.deep_link)`. Count badge shown when `alert.count > 1`. Hidden when no alerts.
- Toast: fixed-position error overlay above tab bar. `role="alert"`, `aria-live="assertive"`. Auto-dismisses via `$effect` after 5 seconds. Triggered via `window.dispatchEvent(new CustomEvent('farm:toast', ...))`.
- CommandButton: spinner-wrapped button with `aria-disabled` and `aria-busy` during in-flight state. Three variants: default, approve (accent background), reject (muted border). `Loader2` Lucide icon with CSS spin animation.
- HealthBadge: GOOD/WARN/CRIT pill badge, color-coded (accent/stale/offline), `aria-label="Zone health: {Good|Warning|Critical}"`.
- +layout.svelte: rewritten to own WebSocket lifecycle (`onMount: connect`, `onDestroy: disconnect`), header with WS status dot, AlertBar, TabBar, Toast all wired in.
- ZoneCard: extended with `goto()` navigation to `/zones/${zone.zone_id}`, `role="button"`, `tabindex="0"`, `onkeydown` for Enter/Space, `cursor: pointer`, HealthBadge in header row.
- +page.svelte: simplified (header moved to layout), `healthScore={dashboardStore.zoneHealthScores.get(zone.zone_id)?.score}` passed to each ZoneCard.
- Three route stubs created: `/coop`, `/zones/[id]`, `/recommendations` — each imports dashboardStore and renders a heading + placeholder paragraph per the plan spec.

## Task Commits

Each task was committed atomically:

1. **Task 1: WebSocket store extension + shared components (TabBar, AlertBar, Toast, CommandButton, HealthBadge)** - `b849711` (feat)
2. **Task 2: Layout rewrite + route scaffolds + ZoneCard extension** - `32c53cd` (feat)

## Files Created/Modified

- `hub/dashboard/src/lib/ws.svelte.ts` — Added 7 Phase 2 state fields; extended snapshot handler; added 7 delta type handlers after existing heartbeat handler
- `hub/dashboard/src/lib/TabBar.svelte` — New: 3-tab bottom nav bar with isActive() function, accent underline, aria-label="Main navigation"
- `hub/dashboard/src/lib/AlertBar.svelte` — New: P0/P1 alert rows, role="alert", goto() deep-link navigation, count badge
- `hub/dashboard/src/lib/Toast.svelte` — New: Fixed-position error toast, 5s auto-dismiss via $effect, role="alert"
- `hub/dashboard/src/lib/CommandButton.svelte` — New: aria-disabled/aria-busy spinner wrapper, approve/reject/default variants
- `hub/dashboard/src/lib/HealthBadge.svelte` — New: GOOD/WARN/CRIT pill with health score color mapping, aria-label
- `hub/dashboard/src/routes/+layout.svelte` — Rewritten: WebSocket lifecycle, header, AlertBar, TabBar, Toast
- `hub/dashboard/src/routes/+page.svelte` — Simplified: removed old header/lifecycle; added healthScore prop to ZoneCard
- `hub/dashboard/src/lib/ZoneCard.svelte` — Extended: goto() navigation, role=button, HealthBadge in zone-header row
- `hub/dashboard/src/routes/coop/+page.svelte` — New stub: "Coop" heading + placeholder
- `hub/dashboard/src/routes/zones/[id]/+page.svelte` — New stub: dynamic zone ID heading + placeholder
- `hub/dashboard/src/routes/recommendations/+page.svelte` — New stub: "Recommendations" heading + placeholder

## Decisions Made

- Toast uses window CustomEvent (`farm:toast`) for dispatch — avoids prop drilling through all feature pages; layout listens and owns the Toast component
- WebSocket lifecycle in +layout.svelte not +page.svelte — prevents reconnect thrashing when navigating between tabs; single connect/disconnect for the app session
- Route stubs are intentional scaffolds per plan spec — plans 02-05 and 02-06 will replace the placeholder content with full implementations

## Deviations from Plan

### Pre-existing Work Discovered

**[Continuation Context] Task 1 already committed from prior agent run**
- **Found during:** Plan start
- **Situation:** Commit `b849711` already contained all Task 1 files (ws.svelte.ts, TabBar, AlertBar, Toast, CommandButton, HealthBadge). Task 2 changes were in the working tree but uncommitted; route stubs were missing.
- **Action:** Verified existing files matched plan spec exactly. Created the 3 missing route stubs and committed Task 2 in full.
- **No code was discarded or duplicated.**

## Known Stubs

The following route stubs are intentional per the plan output spec and will be replaced in plans 02-05 and 02-06:

- `hub/dashboard/src/routes/coop/+page.svelte` — placeholder paragraph; CoopPanel implemented in plan 02-05
- `hub/dashboard/src/routes/zones/[id]/+page.svelte` — placeholder paragraph; zone detail with sensor charts and irrigation controls in plan 02-05
- `hub/dashboard/src/routes/recommendations/+page.svelte` — placeholder paragraph; RecommendationCard queue in plan 02-06

These stubs do NOT prevent plan 02-04's goal from being achieved. The goal of this plan is the app shell (routing, layout, shared components, WebSocket extension) — which is fully delivered. The stubs are the intended output of this plan per the plan spec.

## Self-Check: PASSED

- hub/dashboard/src/lib/TabBar.svelte: FOUND
- hub/dashboard/src/lib/AlertBar.svelte: FOUND
- hub/dashboard/src/lib/Toast.svelte: FOUND
- hub/dashboard/src/lib/CommandButton.svelte: FOUND
- hub/dashboard/src/lib/HealthBadge.svelte: FOUND
- hub/dashboard/src/lib/ws.svelte.ts: FOUND (contains alert_state, recommendation_queue, actuator_state handlers)
- hub/dashboard/src/routes/+layout.svelte: FOUND (contains TabBar, AlertBar, Toast)
- hub/dashboard/src/routes/coop/+page.svelte: FOUND
- hub/dashboard/src/routes/zones/[id]/+page.svelte: FOUND
- hub/dashboard/src/routes/recommendations/+page.svelte: FOUND
- hub/dashboard/src/lib/ZoneCard.svelte: FOUND (contains goto, role=button, HealthBadge)
- Commit b849711 (Task 1): FOUND
- Commit 32c53cd (Task 2): FOUND
- svelte-kit sync: exits 0

---
*Phase: 02-actuator-control-alerts-and-dashboard-v1*
*Completed: 2026-04-10*
