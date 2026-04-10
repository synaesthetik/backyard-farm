---
phase: 03-flock-management-and-unified-dashboard
plan: 02
subsystem: dashboard
tags: [svelte, typescript, websocket, home-tab, flock-summary, zone-card, tabbar, routing]
dependency_graph:
  requires:
    - 03-01 (flock backend core — egg estimator, feed consumption, bridge flock loop)
  provides:
    - FlockSummaryCard.svelte (compact flock overview for Home tab)
    - ZoneCard compact variant (compact prop for Home tab grid)
    - TabBar 4-tab layout (Home/Zones/Coop/Recs)
    - /zones route (zones list moved from /)
    - / route (Home tab unified overview)
    - WS store eggCount field with raw_weight_grams (consumed by Plan 03-04 tare button)
    - WS store feedConsumption field
    - NestingBoxDelta and FeedConsumptionDelta TypeScript types
  affects:
    - 03-03 (ProductionChart reads eggCount from dashboardStore)
    - 03-04 (FlockSettings tare button reads eggCount.raw_weight_grams)
    - 03-05 (CoopPanel egg count section reads dashboardStore.eggCount)
tech_stack:
  added: []
  patterns:
    - Svelte 5 $state/$derived reactivity for new store fields
    - compact prop pattern for ZoneCard dual-mode rendering ({#if compact})
    - ZoneCard compact: single-row layout (badge + name + moisture)
    - FlockSummaryCard: door state badge color mapping (OPEN=accent, CLOSED=secondary, MOVING=stale, STUCK=offline)
    - TabBar exact-match for Home tab ('=== /'), prefix-match for all others
    - Home tab 2-column desktop grid with FlockSummaryCard in right column
    - Vitest + @testing-library/svelte mock pattern for store-dependent components
key_files:
  created:
    - hub/dashboard/src/lib/FlockSummaryCard.svelte
    - hub/dashboard/src/lib/FlockSummaryCard.test.ts
    - hub/dashboard/src/routes/zones/+page.svelte
  modified:
    - hub/dashboard/src/lib/types.ts
    - hub/dashboard/src/lib/ws.svelte.ts
    - hub/dashboard/src/lib/TabBar.svelte
    - hub/dashboard/src/lib/ZoneCard.svelte
    - hub/dashboard/src/routes/+page.svelte
decisions:
  - "Trend indicator shows Minus/neutral when expected production is not yet in store (Plan 03-03 wires expected values)"
  - "Home tab mobile layout: FlockSummaryCard first (CSS order:1), zone cards below (order:2)"
  - "Home tab desktop: CSS grid 2-column, zones-col grid-column:1, flock-col grid-column:2"
  - "ZoneCard compact moisture display uses toFixed(0) — integer percentage, consistent with UI-SPEC number format"
  - "Door badge on FlockSummaryCard uses border-color styling (not background fill) to distinguish from HealthBadge"
metrics:
  duration: ~15 minutes
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_created: 3
  files_modified: 5
  tests_added: 4
  tests_total: 49
---

# Phase 3 Plan 02: Home Tab and Unified Dashboard Summary

**One-liner:** 4-tab navigation with Home tab as unified farm overview — compact zone cards and FlockSummaryCard tapping through to Coop, with WS store extended for Phase 3 flock deltas including raw_weight_grams for downstream tare button.

## What Was Built

Task 1 established the Phase 3 frontend data layer:

- **`types.ts`**: Added `FlockConfig`, `NestingBoxDelta`, `FeedConsumptionDelta` interfaces. Extended `DashboardSnapshot` with `egg_count` and `feed_consumption` fields. Added `NestingBoxDelta` and `FeedConsumptionDelta` to the `WSMessage` union type.

- **`ws.svelte.ts`**: Added `eggCount` and `feedConsumption` `$state` fields to `DashboardStore`. The `eggCount` shape includes `raw_weight_grams: number | null` so Plan 03-04's tare button can read the current sensor weight. Added snapshot handler population and two new delta handlers (`nesting_box` → `eggCount`, `feed_consumption` → `feedConsumption`).

- **`TabBar.svelte`**: Updated from 3 to 4 tabs. Added `LayoutDashboard` icon for Home tab at position 1. Updated `isActive` to use exact match for `/` (Home) and prefix match for `/zones` — prevents Home from activating on zone detail routes.

- **`hub/dashboard/src/routes/zones/+page.svelte`**: Created — zones list moved from `/` to `/zones`. Content is identical to the old `+page.svelte` (zones grid + SystemHealthPanel).

Task 2 built the Home tab UI:

- **`FlockSummaryCard.svelte`**: Full-width card on Home tab. Reads `dashboardStore.eggCount` and `dashboardStore.actuatorStates.get('coop_door')`. Renders: left column (Flock label + egg count or "--"), center (door state badge with color mapping), right (trend indicator — Minus/neutral until Plan 03-03 wires expected production). `role="button"`, `tabindex="0"`, `aria-label="Flock summary — tap to see coop detail"`. Keyboard-navigable (Enter/Space → `goto('/coop')`). Hover: `--color-surface-hover`.

- **`ZoneCard.svelte`**: Added `compact` prop (boolean, default `false`). Compact variant renders single-row layout: `HealthBadge` + zone name (truncated, `text-overflow: ellipsis`) + moisture percentage (right-aligned). Uses `{#if compact}...{:else}...{/if}` — full card behavior unchanged.

- **`+page.svelte` (Home tab `/`)**: Replaced old zones-list content. Imports `FlockSummaryCard` and `ZoneCard`. Mobile layout: `FlockSummaryCard` first (`order: 1`), zone cards below (`order: 2`). Desktop (≥640px): CSS grid 2-column — zones left column, flock right column. Empty state: "No zones configured" heading + "Add a zone in settings to get started." body. `FlockSummaryCard` always renders regardless of zone count.

- **`FlockSummaryCard.test.ts`**: 4 tests — null eggCount shows "--", eggCount renders "N eggs today", `role="button"` and `aria-label` present, door state badge shows correct text.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 4d38a65 | feat(03-02): Phase 3 types, WS store flock fields, 4-tab TabBar, zones list moved to /zones |
| 2 | b25f0b9 | feat(03-02): Home tab, FlockSummaryCard, ZoneCard compact variant |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Design Decisions Made During Implementation

**1. Trend indicator deferred to neutral state**
- **Found during:** Task 2 — FlockSummaryCard implementation
- **Issue:** The trend percentage requires `expected_production` which is not yet stored in `dashboardStore`. Plan 03-03 (ProductionChart) will add this data. Without it, computing a percentage is impossible.
- **Decision:** Show `Minus` icon (neutral/flat) with no percentage when `eggCount` is present but expected production is unknown. This is correct per UI-SPEC "flat (75-89% of expected)" mapping and avoids fabricating a number.
- **Tracked as:** Known stub below.

**2. Door badge uses border-color styling**
- **Issue:** HealthBadge uses background-fill for color. For the door state badge on FlockSummaryCard, an outlined pill (border-color) distinguishes it visually from zone health badges while using the same color tokens.
- **Decision:** `border: 1px solid {color}; color: {color}` — outline pill style.

## Known Stubs

**1. FlockSummaryCard trend indicator — no percentage displayed**
- **File:** `hub/dashboard/src/lib/FlockSummaryCard.svelte`
- **Lines:** `trendIcon` and `trendColor` derived functions
- **Reason:** `expected_production` value is not in `dashboardStore` until Plan 03-03 wires the production chart data. The trend percentage ("N%") cannot be computed without it.
- **Resolves in:** Plan 03-03 (ProductionChart) — that plan will add expected production to the store snapshot, enabling the FlockSummaryCard to compute and display the real percentage.
- **Impact:** Trend icon shows `Minus` (neutral) when egg data is present. The card still renders correctly and navigates to `/coop`. This does NOT prevent the plan's goal (Home tab unified overview) from being achieved.

## Self-Check

### Files exist:
- hub/dashboard/src/lib/FlockSummaryCard.svelte — FOUND
- hub/dashboard/src/lib/FlockSummaryCard.test.ts — FOUND
- hub/dashboard/src/routes/zones/+page.svelte — FOUND
- hub/dashboard/src/lib/types.ts — FOUND (modified)
- hub/dashboard/src/lib/ws.svelte.ts — FOUND (modified)
- hub/dashboard/src/lib/TabBar.svelte — FOUND (modified)
- hub/dashboard/src/lib/ZoneCard.svelte — FOUND (modified)
- hub/dashboard/src/routes/+page.svelte — FOUND (modified)

### Commits exist:
- 4d38a65 — Task 1
- b25f0b9 — Task 2

### Test results: 49 passed, 0 failed

### Build: clean (✓ built in 4.23s)

## Self-Check: PASSED
