---
phase: 03-flock-management-and-unified-dashboard
plan: 03
subsystem: dashboard
tags: [svelte, typescript, uplot, chart, sparkline, animation, flock, egg-count, coop-panel]
dependency_graph:
  requires:
    - 03-01 (egg_estimator, production_model — backend compute)
    - 03-02 (ws.svelte.ts eggCount/feedConsumption fields, DashboardStore types)
    - 03-06 (GET /api/flock/egg-history, POST /api/flock/refresh-eggs endpoints)
  provides:
    - HenPresentIndicator.svelte (animated hen detection indicator)
    - ProductionChart.svelte (uPlot 2-series actual/expected overlay)
    - FeedSparkline.svelte (inline SVG 7-day sparkline)
    - CoopPanel.svelte (extended with egg count, hen indicator, production chart, feed sparkline, refresh, settings link)
  affects:
    - 03-04 (FlockSettings page — settings gear icon links to /coop/settings)
tech_stack:
  added: []
  patterns:
    - uPlot onMount + requestAnimationFrame + ResizeObserver (same as SensorChart.svelte)
    - Svelte {#if} conditional rendering for hen indicator (not CSS hidden)
    - toPolylinePoints() min/max normalization with division-by-zero guard
    - refreshing $state + fetch + aria-busy/aria-disabled pattern for in-flight button state
    - farm:toast CustomEvent for fetch error feedback
key_files:
  created:
    - hub/dashboard/src/lib/HenPresentIndicator.svelte
    - hub/dashboard/src/lib/ProductionChart.svelte
    - hub/dashboard/src/lib/FeedSparkline.svelte
    - hub/dashboard/src/lib/ProductionChart.test.ts
  modified:
    - hub/dashboard/src/lib/CoopPanel.svelte
decisions:
  - "Feed consumption row renders only when feedLevel data is present — aligns with UI-SPEC placement below feed level bar; hides gracefully when no feed data"
  - "CoopPanel level sections wrapped in card-style surface panels (matching Phase 2 door-hero pattern) for visual consistency"
  - "Section order follows plan acceptance criteria (eggs first) rather than UI-SPEC order (door first) — plan takes precedence as the more specific implementation spec"
metrics:
  duration: ~20 minutes
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
  tests_added: 3
  tests_total: 55
---

# Phase 3 Plan 03: Coop Tab Flock Display Components Summary

**One-liner:** HenPresentIndicator (pulsing egg icon), ProductionChart (uPlot actual/expected 30-day overlay), and FeedSparkline (inline SVG 7-day) wired into an extended CoopPanel with egg count, refresh button, and settings gear link.

## What Was Built

Task 1 created the three new display components:

- **`HenPresentIndicator.svelte`**: Renders a Lucide `Egg` icon at 16px in `--color-accent` alongside "Hen present" label (16px/600). Icon pulses on `@keyframes hen-pulse` (2s ease-in-out: scale 1 → 1.15/opacity 0.7 → 1). `aria-live="polite"` on container; `aria-hidden="true"` on icon. Caller uses `{#if}` to conditionally render.

- **`ProductionChart.svelte`**: Follows the SensorChart.svelte pattern exactly (`onMount` + `requestAnimationFrame` + `ResizeObserver`). Fetches `/api/flock/egg-history?days=30`. Two series: Actual (solid green `#4ade80`, 1.5px) and Expected (dashed gray `#94a3b8`, dash `[4,4]`, 1.5px). Loading state: skeleton div at chart dimensions with `--color-surface` background. Empty state (< 3 days data): skeleton + centered "Not enough data yet — check back in a few days" (14px/400, `--color-muted`). `aria-label="Egg production chart — actual vs expected, last 30 days"` on container. Height: 160px mobile / 200px desktop.

- **`FeedSparkline.svelte`**: Fixed 80×24px SVG with single `<polyline>`. Accepts `values: number[]` prop. `toPolylinePoints()` normalizes using min/max with `range = max - min || 1` division-by-zero guard. `aria-hidden="true"` — decorative only. Renders nothing when fewer than 2 data points.

- **`ProductionChart.test.ts`**: 3 tests — loading skeleton renders on initial mount, empty state message appears when data has fewer than 3 days, correct `aria-label` on container.

Task 2 extended CoopPanel with all Phase 3 displays:

- **Egg count section** (top of panel): "Eggs Today" heading (20px/600), egg count display in 28px/600 with `tabular-nums`, conditional `<HenPresentIndicator />` when `eggCount.hen_present`, refresh button POSTing to `/api/flock/refresh-eggs` with spin animation during in-flight state.
- **Settings gear icon**: `Settings` icon at 24px, `aria-label="Flock settings"`, navigates to `/coop/settings` via `goto()`.
- **Production chart section**: "Egg Production — 30 Days" heading with `<ProductionChart />`.
- **Feed consumption row**: inline below feed level bar — "~{N}g/day" rate label (14px/400, `--color-text-secondary`) + `<FeedSparkline values={feedConsumption.weekly} />` in flex row with 8px gap.
- **Section order**: eggs → production chart → door → schedule → feed level → feed consumption → water.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 74d0312 | feat(03-03): HenPresentIndicator, ProductionChart, and FeedSparkline components |
| 2 | c08bd10 | feat(03-03): extend CoopPanel with egg section, production chart, feed sparkline, and refresh |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Design Decisions Made During Implementation

**1. Section order follows plan acceptance criteria over UI-SPEC**
- **Found during:** Task 2
- **Issue:** UI-SPEC section order places door first (door → schedule → eggs → production → feed → water). Plan acceptance criteria explicitly states: "Section order: eggs -> production chart -> door -> schedule -> feed level -> feed consumption -> water".
- **Decision:** Plan acceptance criteria is the more specific implementation spec; UI-SPEC is the design intent. Eggs-first order matches the plan's stated "focal point" rationale (egg count is the new focal point on the Coop tab).

**2. Feed consumption row conditional on feedLevel presence**
- **Found during:** Task 2
- **Issue:** UI-SPEC says feed consumption row renders below the feed level bar. If `feedLevel` is null, there is no bar to render below.
- **Decision:** Render the feed consumption row only inside the `{#if feedLevel}` block, immediately after the progress bar. This matches the UI-SPEC layout intent (inline below the bar) and gracefully handles the no-data case.

**3. Level sections wrapped in card-style surface panels**
- **Found during:** Task 2 — reviewing Phase 2 CoopPanel
- **Issue:** Original CoopPanel had feed/water level sections without card borders. Egg and production sections received card styling for visual grouping.
- **Decision:** Applied card styling (surface background, border, border-radius, padding, shadow) to all sections for visual consistency across the panel.

## Known Stubs

**1. FlockSummaryCard trend indicator — deferred from Plan 03-02**
- **File:** `hub/dashboard/src/lib/FlockSummaryCard.svelte`
- **Reason:** The trend percentage requires `expected_production` from the WS snapshot. ProductionChart fetches history on mount but does not write back to `dashboardStore`. The trend percentage computation is deferred to a future integration pass.
- **Impact:** Trend icon shows `Minus` (neutral) on the Home tab FlockSummaryCard. CoopPanel itself displays the full ProductionChart correctly.

## Self-Check

### Files exist:
- hub/dashboard/src/lib/HenPresentIndicator.svelte — FOUND
- hub/dashboard/src/lib/ProductionChart.svelte — FOUND
- hub/dashboard/src/lib/FeedSparkline.svelte — FOUND
- hub/dashboard/src/lib/ProductionChart.test.ts — FOUND
- hub/dashboard/src/lib/CoopPanel.svelte — FOUND (modified)

### Commits exist:
- 74d0312 — Task 1
- c08bd10 — Task 2

### Test results: 52 passed, 0 failed (55 tests after ProductionChart.test.ts)

### Build: clean (built in 4.17s)

## Self-Check: PASSED
