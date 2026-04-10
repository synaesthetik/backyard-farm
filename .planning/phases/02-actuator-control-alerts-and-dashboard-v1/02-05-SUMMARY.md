---
phase: 02-actuator-control-alerts-and-dashboard-v1
plan: 05
subsystem: dashboard
tags: [svelte5, sveltekit, typescript, uplot, charts, irrigation, coop, recommendations]

# Dependency graph
requires:
  - phase: 02-actuator-control-alerts-and-dashboard-v1
    plan: 03
    provides: GET /api/zones/{zone_id}/history, POST /api/recommendations/{id}/approve|reject, POST /api/actuators/irrigate|coop-door
  - phase: 02-actuator-control-alerts-and-dashboard-v1
    plan: 04
    provides: DashboardStore with Phase 2 state, route stubs (zones/[id], coop, recommendations), CommandButton, HealthBadge, Toast

provides:
  - SensorChart.svelte — uPlot canvas time-series chart, dark theme, ResizeObserver, 7/30-day toggle, loading skeleton, empty state
  - RecommendationCard.svelte — approve/reject with POST to recommendation endpoints, farm:toast on error
  - CoopPanel.svelte — door state with color mapping, Open/Close door controls, schedule display, feed/water progress bars
  - zones/[id]/+page.svelte — full zone detail: irrigation controls, SensorValue readings, 3 SensorChart instances
  - coop/+page.svelte — CoopPanel delegate
  - recommendations/+page.svelte — RecommendationCard queue or empty state

affects:
  - 02-06 (PWA service worker — app shell now complete with all feature pages)

# Tech tracking
tech-stack:
  added:
    - uPlot (MIT, ~45KB canvas-based time-series charting library)
  patterns:
    - SensorChart uses requestAnimationFrame before reading clientWidth to avoid zero-width on mount (Pitfall 2)
    - ResizeObserver on chart container calls chart.setSize() for responsive resize without re-fetch
    - $effect(() => { if (days) loadAndRender(); }) re-fetches on range toggle without onMount re-run
    - farm:toast CustomEvent dispatched from feature pages — layout owns Toast, no prop drilling

key-files:
  created:
    - hub/dashboard/src/lib/SensorChart.svelte
    - hub/dashboard/src/lib/RecommendationCard.svelte
    - hub/dashboard/src/lib/CoopPanel.svelte
  modified:
    - hub/dashboard/src/routes/zones/[id]/+page.svelte
    - hub/dashboard/src/routes/coop/+page.svelte
    - hub/dashboard/src/routes/recommendations/+page.svelte
    - hub/dashboard/package.json (added uPlot dependency)
    - hub/dashboard/package-lock.json

key-decisions:
  - "SensorValue icon prop takes a Lucide Component reference (not a string) — zone detail page imports Droplets, FlaskConical, Thermometer and passes them directly"
  - "SensorChart $effect re-fetches on days change — avoids duplicate fetch on mount by gating on days truthiness; onMount handles initial load"
  - "CoopPanel doorLoading tracks which direction ('open'|'close'|null) to show spinner on the correct button when moving state is not yet confirmed"

# Metrics
duration: 12min
completed: 2026-04-09
---

# Phase 2 Plan 05: Feature Pages — Zone Detail, Coop Panel, Recommendation Queue Summary

**uPlot time-series charts, full zone detail with irrigation controls, CoopPanel with door/feed/water, and RecommendationCard queue — all three feature page stubs replaced with complete implementations**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-09
- **Completed:** 2026-04-09
- **Tasks:** 2
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- SensorChart.svelte: wraps uPlot with dark theme config matching UI-SPEC (grid `#2d3149`, axis stroke `#94a3b8`, axis size 14, cursor `#6b7280`). Per-sensor series colors: moisture `#4ade80`, pH `#60a5fa`, temperature `#fb923c`. Fetches from `/api/zones/${zoneId}/history`. requestAnimationFrame before `clientWidth` read on mount. ResizeObserver for responsive resize. $effect re-fetches on days change. Loading skeleton and "No data for this period" empty state both implemented.

- RecommendationCard.svelte: approve POSTs to `/api/recommendations/{id}/approve`, reject to `…/reject`. Separate `approveLoading`/`rejectLoading` state — each button shows spinner independently. 409 response dispatches "Another zone is already irrigating." toast; all other errors dispatch "Command failed — tap to retry". Card removal on success is driven by WebSocket `recommendation_queue` delta (no client-side removal logic needed).

- CoopPanel.svelte: door state from `dashboardStore.actuatorStates.get('coop_door')`. Color mapping per UI-SPEC (open=accent, closed=text-secondary, moving=stale, stuck=offline). DoorOpen/DoorClosed Lucide icons swap on state. `aria-live="polite"` on door state div. Schedule formatted with `toLocaleTimeString('en-GB', { hour12: false })` for 24-hour display. Feed progress bar fill: accent above threshold, stale below. Water progress bar fill: `#60a5fa` above, stale below.

- zones/[id]/+page.svelte: stub replaced with full implementation. Irrigation controls at top (Open valve / Close valve). SensorValue rows using Droplets/FlaskConical/Thermometer Lucide components. "Sensor History" section heading with 7/30-day range toggle buttons. Three SensorChart instances with `bind:days={chartDays}`.

- coop/+page.svelte: one-line delegate to CoopPanel.

- recommendations/+page.svelte: RecommendationCard list keyed by `recommendation_id`, or empty state ("No recommendations" / "Sensor thresholds are within range.").

- Build: `npm run build` exits 0 with no new errors or warnings from this plan's changes.

## Task Commits

Each task was committed atomically:

1. **Task 1: uPlot install + SensorChart + RecommendationCard + CoopPanel** — `c8d5a9f` (feat)
2. **Task 2: Wire feature pages — zone detail, coop, recommendations** — `318aaea` (feat)

## Files Created/Modified

- `hub/dashboard/package.json` — uPlot added to dependencies
- `hub/dashboard/src/lib/SensorChart.svelte` — New: uPlot wrapper, dark theme, fetch /api/zones/{id}/history, ResizeObserver, empty/loading states
- `hub/dashboard/src/lib/RecommendationCard.svelte` — New: approve/reject with POST, separate loading states, farm:toast on error
- `hub/dashboard/src/lib/CoopPanel.svelte` — New: door state/controls/schedule, feed/water progress bars, color-coded thresholds
- `hub/dashboard/src/routes/zones/[id]/+page.svelte` — Stub replaced: irrigation controls, SensorValue rows, SensorChart x3 with range toggle
- `hub/dashboard/src/routes/coop/+page.svelte` — Stub replaced: CoopPanel delegate
- `hub/dashboard/src/routes/recommendations/+page.svelte` — Stub replaced: RecommendationCard queue with empty state

## Decisions Made

- SensorValue `icon` prop is a Lucide Component reference (not a string icon name) — discovered by reading the actual component interface; zone detail page imports and passes Droplets, FlaskConical, Thermometer directly
- SensorChart $effect re-fetches on `days` change — initial load handled by onMount; $effect gates on `days` truthiness to avoid double-fetch on mount
- CoopPanel tracks `doorLoading` as `'open' | 'close' | null` rather than boolean — enables spinner on the correct button when the door is already in a moving state from WebSocket update

## Deviations from Plan

### Auto-adjusted: SensorValue prop interface

**[Rule 1 - Bug] Used correct Lucide Component references for SensorValue icon prop**
- **Found during:** Task 2
- **Issue:** The plan's example code used string names like `icon="droplet"` for SensorValue, but the actual SensorValue component interface takes `icon: Component` (a Svelte component reference). Passing a string would cause a runtime error.
- **Fix:** Imported `Droplets`, `FlaskConical`, `Thermometer` from `lucide-svelte` and passed them as `icon={Droplets}` etc.
- **Files modified:** `hub/dashboard/src/routes/zones/[id]/+page.svelte`
- **No SensorValue component changes needed.**

## Known Stubs

None. All three route stubs from plan 02-04 have been replaced with full implementations. All REST API calls are wired to real endpoints. Progress bars and charts display live data from WebSocket store and REST history endpoint.

## Self-Check: PASSED

- hub/dashboard/src/lib/SensorChart.svelte: FOUND (contains import uPlot, requestAnimationFrame, ResizeObserver, size: 14, No data for this period)
- hub/dashboard/src/lib/RecommendationCard.svelte: FOUND (contains api/recommendations, Approve, Reject, farm:toast)
- hub/dashboard/src/lib/CoopPanel.svelte: FOUND (contains Coop Door, Today's schedule, Feed, Water, % full)
- hub/dashboard/src/routes/zones/[id]/+page.svelte: FOUND (contains SensorChart, CommandButton, api/actuators/irrigate, Open valve, Close valve, Sensor History, 7 days, 30 days, farm:toast)
- hub/dashboard/src/routes/coop/+page.svelte: FOUND (contains CoopPanel)
- hub/dashboard/src/routes/recommendations/+page.svelte: FOUND (contains RecommendationCard, No recommendations, Sensor thresholds are within range.)
- Commit c8d5a9f (Task 1): FOUND
- Commit 318aaea (Task 2): FOUND
- npm run build: exits 0

---
*Phase: 02-actuator-control-alerts-and-dashboard-v1*
*Completed: 2026-04-09*
