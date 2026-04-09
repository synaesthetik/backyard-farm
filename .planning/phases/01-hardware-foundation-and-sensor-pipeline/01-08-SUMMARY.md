---
phase: 01-hardware-foundation-and-sensor-pipeline
plan: 08
subsystem: dashboard-testing
tags: [testing, svelte, vitest, unit-tests, gap-closure]
dependency_graph:
  requires: []
  provides:
    - dashboard unit test suite (SensorValue, ZoneCard, NodeHealthRow)
    - vitest browser-condition resolution for Svelte 5 + jsdom
  affects:
    - hub/dashboard/src/lib/ZoneCard.svelte (bug fix applied)
tech_stack:
  added: []
  patterns:
    - "@testing-library/svelte render() with top-level props (Svelte 5 API)"
    - "afterEach cleanup() for test isolation"
    - "$derived.by(fn) for multi-line derived values in Svelte 5"
    - "vitest resolve.conditions=[browser] for Svelte 5 + jsdom"
key_files:
  created:
    - hub/dashboard/src/lib/SensorValue.test.ts
    - hub/dashboard/src/lib/ZoneCard.test.ts
    - hub/dashboard/src/lib/NodeHealthRow.test.ts
  modified:
    - hub/dashboard/vitest.config.ts
    - hub/dashboard/src/lib/ZoneCard.svelte
decisions:
  - "Use $derived.by(fn) not $derived(fn) for function-body derived values in Svelte 5"
  - "Add resolve.conditions=[browser] to vitest config to prevent Svelte resolving server entry in jsdom"
metrics:
  duration: "4m 5s"
  completed: "2026-04-09T16:23:42Z"
  tasks_completed: 2
  files_created: 3
  files_modified: 2
---

# Phase 01 Plan 08: Dashboard Component Unit Tests Summary

Three missing dashboard component unit tests created and passing. `npx vitest run` exits 0 with 19 tests across SensorValue, ZoneCard, and NodeHealthRow test files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create SensorValue.test.ts | b7bac2f | SensorValue.test.ts, vitest.config.ts |
| 2 | Create ZoneCard.test.ts and NodeHealthRow.test.ts | 1ddd679 | ZoneCard.test.ts, NodeHealthRow.test.ts, ZoneCard.svelte |

## Test Coverage

**SensorValue.test.ts (8 tests):**
- Value with unit formatting (`45.3%`)
- Null value renders `--`
- GOOD quality badge rendered
- SUSPECT quality badge rendered
- BAD quality badge rendered
- No badge when quality is null
- Label text rendered
- Temperature rounded to integer (`22.7°C` → `23°C`)

**ZoneCard.test.ts (6 tests):**
- zone_id rendered as heading
- "No data received" when all sensors null
- Sensor values rendered when readings provided
- `.stale` CSS class applied when received_at older than 5 minutes
- "Stuck sensor detected" shown when any sensor has stuck=true
- No stuck indicator when all sensors stuck=false

**NodeHealthRow.test.ts (5 tests):**
- node_id text rendered
- ONLINE badge when isOffline=false
- OFFLINE badge when isOffline=true
- Heartbeat elapsed text when online and recent
- "Last seen Nm ago" text when offline

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Add `resolve.conditions: ['browser']` to vitest config**
- **Found during:** Task 1 (first test run)
- **Issue:** Svelte 5's `package.json` exports map `worker` and `default` conditions to `index-server.js`. Vitest running jsdom uses neither `browser` nor `worker` to select the client entry, causing `mount(...)` is not available on the server error on every test.
- **Fix:** Added `resolve: { conditions: ['browser'] }` to `vitest.config.ts` so Svelte resolves its client-side entry point during tests.
- **Files modified:** `hub/dashboard/vitest.config.ts`
- **Commit:** b7bac2f

**2. [Rule 1 - Bug] Fix `$derived(fn)` → `$derived.by(fn)` in ZoneCard.svelte**
- **Found during:** Task 2 (ZoneCard test failures)
- **Issue:** `ZoneCard.svelte` used `$derived((): string | null => { ... })` for `latestReceivedAt`, `zoneIsStale`, and `zoneIsStuck`. In Svelte 5, `$derived(expr)` stores the _result_ of evaluating `expr` — when `expr` is an arrow function literal, the derived value becomes the function object itself (always truthy). Consequences: the stale border was always applied; "No data received" was never shown; stuck indicator was always shown.
- **Fix:** Changed all three from `$derived(fn)` to `$derived.by(fn)`. `$derived.by(fn)` calls `fn()` and stores its return value, which is the intended Svelte 5 API for function-body derived computation.
- **Files modified:** `hub/dashboard/src/lib/ZoneCard.svelte`
- **Commit:** 1ddd679

**3. [Rule 2 - Missing critical] Add `afterEach(cleanup)` for test isolation**
- **Found during:** Task 1 (multiple-elements errors after cleanup fix)
- **Issue:** Without explicit cleanup, renders from prior tests accumulate in the DOM, causing `getByText` to find multiple matching elements.
- **Fix:** Added `afterEach(() => cleanup())` to all three test files using the `cleanup` export from `@testing-library/svelte`.
- **Commit:** b7bac2f (SensorValue), 1ddd679 (ZoneCard, NodeHealthRow)

## Known Stubs

None — all tests use real component renders against live component logic.

## Verification

```
cd hub/dashboard && npx vitest run
# Test Files  3 passed (3)
# Tests       19 passed (19)
# Exit code: 0
```

## Self-Check: PASSED

- `hub/dashboard/src/lib/SensorValue.test.ts` — exists
- `hub/dashboard/src/lib/ZoneCard.test.ts` — exists
- `hub/dashboard/src/lib/NodeHealthRow.test.ts` — exists
- Commit b7bac2f — exists (SensorValue tests + vitest config)
- Commit 1ddd679 — exists (ZoneCard + NodeHealthRow tests + ZoneCard bug fix)
- `npx vitest run` exits 0 with 19 tests passing
