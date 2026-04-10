---
phase: 02-actuator-control-alerts-and-dashboard-v1
plan: 06
subsystem: dashboard
tags: [svelte5, sveltekit, pwa, service-worker, vitest, testing-library, typescript]

# Dependency graph
requires:
  - phase: 02-actuator-control-alerts-and-dashboard-v1
    plan: 05
    provides: AlertBar, HealthBadge, CommandButton, RecommendationCard, CoopPanel, SensorChart — all Phase 2 components

provides:
  - service-worker.ts — SvelteKit PWA service worker, app shell cache (farm-${version}), /api/* and /ws/* excluded
  - manifest.webmanifest — updated with orientation: portrait, theme_color aligned to #0f1117
  - AlertBar.test.ts — 6 tests: P0/P1 rendering, count badge, empty state, tappable row
  - HealthBadge.test.ts — 6 tests: GOOD/WARN/CRIT text content, aria-label per score
  - CommandButton.test.ts — 7 tests: label, spinner on loading, aria-disabled/aria-busy, approve variant class
  - RecommendationCard.test.ts — 7 tests: field rendering, Approve/Reject buttons, fetch mock on click
  - src/__mocks__/navigation.ts — $app/navigation stub for test environment
  - src/__mocks__/stores.ts — $app/stores stub for test environment

affects:
  - Human verification (Task 3 checkpoint: complete Phase 2 experience on mobile/desktop)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - vitest.config.ts alias pattern: $lib -> src/lib, $app/navigation -> src/__mocks__/navigation.ts resolves SvelteKit virtual module imports in jsdom test environment
    - Service worker pattern: versioned cache name farm-${version}, skip /api/* and /ws/* in fetch handler, delete old caches on activate

key-files:
  created:
    - hub/dashboard/src/service-worker.ts
    - hub/dashboard/src/lib/AlertBar.test.ts
    - hub/dashboard/src/lib/HealthBadge.test.ts
    - hub/dashboard/src/lib/CommandButton.test.ts
    - hub/dashboard/src/lib/RecommendationCard.test.ts
    - hub/dashboard/src/__mocks__/navigation.ts
    - hub/dashboard/src/__mocks__/stores.ts
  modified:
    - hub/dashboard/static/manifest.webmanifest
    - hub/dashboard/src/app.html
    - hub/dashboard/vitest.config.ts

key-decisions:
  - "vitest.config.ts alias for $lib and $app/* virtual modules — required because SvelteKit path aliases are not set up by default in vitest; all 7 test files (including pre-existing ZoneCard.test.ts) now pass"
  - "Manifest icon paths kept as /icons/icon-192.png and /icons/icon-512.png — existing icons live under static/icons/, not static/ root; the plan's example paths were illustrative, not prescriptive"
  - "theme_color aligned to #0f1117 (--color-bg) in both manifest and app.html — was #1c1f2b (--color-surface) before; #0f1117 matches UI-SPEC PWA contract"

requirements-completed: [UI-05, IRRIG-02, AI-04, AI-05]

# Metrics
duration: 18min
completed: 2026-04-09
---

# Phase 2 Plan 06: PWA Service Worker, Manifest, and Component Tests Summary

**SvelteKit PWA service worker with versioned app shell cache, all 4 Phase 2 component test suites (45 tests passing), and vitest $lib/$app alias fix enabling the full test suite**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-09
- **Completed:** 2026-04-09
- **Tasks:** 2 (Task 3 is checkpoint:human-verify — awaiting human)
- **Files modified:** 10 (7 created, 3 modified)

## Accomplishments

- service-worker.ts: pre-caches app shell using SvelteKit's `$service-worker` virtual module (build + files arrays). Cache named `farm-${version}` — old caches deleted on activate. Fetch handler skips /api/* and /ws/* to ensure data endpoints are never cached offline. Strictly follows D-33.

- manifest.webmanifest: added `orientation: "portrait"` (was missing). Aligned `theme_color` to `#0f1117` (--color-bg) from `#1c1f2b`. Icon paths kept as `/icons/icon-192.png` and `/icons/icon-512.png` matching the actual files in `static/icons/`.

- app.html: theme-color meta updated to `#0f1117` to match manifest.

- AlertBar.test.ts (6 tests): P0 row has `.alert-row.p0` class, P1 row has `.alert-row.p1`, count badge appears when count > 1, no badge when count = 1, component does not render when alerts is empty, rows are `<button>` elements (tappable).

- HealthBadge.test.ts (6 tests): GOOD/WARN/CRIT text content per score, aria-label "Zone health: Good/Warning/Critical" per score.

- CommandButton.test.ts (7 tests): label text shown when idle, label hidden when loading, spinner present when loading, aria-disabled=true when loading, aria-busy=true when loading, button.disabled=true when loading, approve variant has `.approve` CSS class.

- RecommendationCard.test.ts (7 tests): action_description, sensor_reading, explanation all rendered, Approve and Reject buttons present, clicking Approve calls fetch with correct approve URL, clicking Reject calls fetch with correct reject URL.

- vitest.config.ts fix: added `$lib` → `src/lib` and `$app/navigation` → `src/__mocks__/navigation.ts` aliases. This fixed the pre-existing ZoneCard.test.ts failure (was failing since Phase 1) and enabled RecommendationCard.test.ts to resolve `$lib/CommandButton.svelte`. All 45 tests now pass across 7 test files.

- Production build: `npm run build` exits 0, no new errors or warnings.

## Task Commits

Each task was committed atomically:

1. **Task 1: PWA service worker + manifest update** — `cc6facc` (feat)
2. **Task 2: Component unit tests + vitest alias fixes** — `471b8e8` (feat)

Task 3 is checkpoint:human-verify — no commit yet.

## Files Created/Modified

- `hub/dashboard/src/service-worker.ts` — New: SvelteKit service worker, app shell cache, skip /api/* /ws/*
- `hub/dashboard/static/manifest.webmanifest` — Added orientation: portrait, aligned theme_color to #0f1117
- `hub/dashboard/src/app.html` — theme-color meta updated to #0f1117
- `hub/dashboard/vitest.config.ts` — Added $lib and $app/navigation aliases for test environment
- `hub/dashboard/src/__mocks__/navigation.ts` — New: $app/navigation stub (goto, invalidate, etc.)
- `hub/dashboard/src/__mocks__/stores.ts` — New: $app/stores stub (page, navigating, updated)
- `hub/dashboard/src/lib/AlertBar.test.ts` — New: 6 tests
- `hub/dashboard/src/lib/HealthBadge.test.ts` — New: 6 tests
- `hub/dashboard/src/lib/CommandButton.test.ts` — New: 7 tests
- `hub/dashboard/src/lib/RecommendationCard.test.ts` — New: 7 tests

## Decisions Made

- vitest.config.ts alias approach chosen over per-file `vi.mock()` calls — centralizing the alias means all existing and future test files get the mock automatically without boilerplate in each file.
- Manifest icon paths kept as `/icons/icon-192.png` — plan example used `/icon-192.png` (root) but actual icon files are in `static/icons/`. Kept path consistent with existing files rather than moving them.
- theme_color set to `#0f1117` (--color-bg) per UI-SPEC PWA contract. Previous value `#1c1f2b` was --color-surface; #0f1117 is correct per spec.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pre-existing vitest alias gap that blocked test suite from passing**
- **Found during:** Task 2 (running npm test -- --run)
- **Issue:** ZoneCard.test.ts and RecommendationCard.test.ts failed because vitest had no aliases for `$lib` (SvelteKit path) or `$app/navigation` (SvelteKit virtual module). This was a pre-existing Phase 1 gap — ZoneCard.test.ts was always failing but not caught because prior summaries checked build, not test exit code.
- **Fix:** Added resolve.alias entries in vitest.config.ts for `$lib` → `src/lib` and `$app/navigation` → `src/__mocks__/navigation.ts`. Created two mock files. Removed per-file vi.mock call from AlertBar.test.ts (now handled globally).
- **Files modified:** hub/dashboard/vitest.config.ts, hub/dashboard/src/__mocks__/navigation.ts, hub/dashboard/src/__mocks__/stores.ts, hub/dashboard/src/lib/AlertBar.test.ts
- **Verification:** All 45 tests pass (7 test files)
- **Committed in:** 471b8e8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking pre-existing test gap)
**Impact on plan:** Essential for meeting the acceptance criterion `npm test -- --run` exits 0. No scope creep.

## Issues Encountered

None beyond the pre-existing vitest alias gap documented above.

## Known Stubs

None. Task 3 is a human verification checkpoint, not a code stub.

## Next Phase Readiness

- PWA is installable: service worker + manifest correctly configured for standalone portrait mode on iOS/Android.
- All 45 frontend tests pass; production build is clean.
- Awaiting Task 3: human verification of complete Phase 2 experience on mobile and desktop.
- After Task 3 approval, Phase 2 is complete.

---
*Phase: 02-actuator-control-alerts-and-dashboard-v1*
*Completed: 2026-04-09*
