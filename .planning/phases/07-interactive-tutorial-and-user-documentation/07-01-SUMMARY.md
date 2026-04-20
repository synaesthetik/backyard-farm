---
phase: 07-interactive-tutorial-and-user-documentation
plan: 01
subsystem: dashboard/tutorial
tags: [tutorial, onboarding, localStorage, svelte5, sveltekit]
dependency_graph:
  requires: []
  provides: [tutorial-wizard-routes, tutorial-welcome-banner, settings-tutorial-tab]
  affects: [hub/dashboard/src/routes/+layout.svelte, hub/dashboard/src/routes/settings/+layout.svelte]
tech_stack:
  added: []
  patterns: [svelte5-runes-$state, localStorage-persistence, sveltekit-file-routing, vitest-static-imports, vi.stubGlobal-localStorage]
key_files:
  created:
    - hub/dashboard/src/routes/tutorial/+layout.svelte
    - hub/dashboard/src/routes/tutorial/+page.svelte
    - hub/dashboard/src/routes/tutorial/1/+page.svelte
    - hub/dashboard/src/routes/tutorial/2/+page.svelte
    - hub/dashboard/src/routes/tutorial/3/+page.svelte
    - hub/dashboard/src/routes/tutorial/4/+page.svelte
    - hub/dashboard/src/routes/tutorial/5/+page.svelte
    - hub/dashboard/src/routes/tutorial/6/+page.svelte
    - hub/dashboard/src/routes/tutorial/7/+page.svelte
    - hub/dashboard/src/routes/tutorial/8/+page.svelte
    - hub/dashboard/src/routes/tutorial/tutorial.test.ts
  modified:
    - hub/dashboard/src/routes/+layout.svelte
    - hub/dashboard/src/routes/settings/+layout.svelte
    - .gitignore
    - README.md
decisions:
  - Static imports in test file over dynamic imports — avoids 5000ms cold-compile timeout on first dynamic import; matches existing test file pattern
  - vi.stubGlobal for localStorage in tests — jsdom localStorage.clear() not available in this environment; per-test store object via stubGlobal provides clean isolation
  - container.querySelector over screen.getByRole for button selection — avoids multiple-element errors when tests render same component in sequence; consistent with project test patterns
metrics:
  duration: 8m
  completed: 2026-04-20T18:38:00Z
  tasks_completed: 2
  tasks_total: 2
  files_created: 11
  files_modified: 4
---

# Phase 7 Plan 01: Interactive Tutorial — Route Scaffold and Welcome Banner Summary

8-step onboarding wizard at `/tutorial/[1-8]` with localStorage progress persistence, auto-launch welcome banner in root layout, Tutorial tab in settings, and full Vitest test coverage.

## What Was Built

### Task 1: Tutorial Route Scaffold

10 SvelteKit route files at `hub/dashboard/src/routes/tutorial/`:

- **`+layout.svelte`** — Tutorial shell with a 4px progress bar (`role="progressbar"`) and step counter. Derives current step from URL pathname. No TabBar/AlertBar — focused wizard experience. Root layout still wraps for WebSocket and toast.
- **`+page.svelte`** — Root redirect: reads `tutorial_step` from localStorage in `onMount`, routes to `/tutorial/{step}` (capped at 8) via `goto` with `replaceState: true`.
- **`1/+page.svelte` through `8/+page.svelte`** — Eight step pages, each self-contained with:
  - `markDone()` writes `tutorial_step = STEP+1` to localStorage and calls `goto(/tutorial/N)` for steps 1–7
  - Step 8 sets `tutorial_completed = 'true'` and removes `tutorial_step` (no goto to /tutorial/9)
  - Back link (`<a href="/tutorial/N-1" class="btn-secondary">`) for steps 2–8
  - "Finish" button on step 8 with `CheckCircle` icon; "I did this" + `ChevronRight` on steps 1–7
  - Step 8 also includes a "Restart Tutorial" button that clears both localStorage keys and goes to `/tutorial/1`
  - `<svelte:head>` title on every page
  - Self-contained CSS using farm design system tokens

**Step content:**
1. Welcome — what the tutorial covers, how to use it
2. First Boot Setup — `docker compose up -d`, `dev-init.sh`, Caddy HTTPS
3. Add Your First Zone — zone config fields, link to `/settings/zones`
4. Verify Sensor Data — quality badge meanings, STALE check, link to `/`
5. Run a Manual Irrigation — valve open/close, single-zone rule, link to `/zones`
6. Set Up Coop Automation — lat/lng, offsets, hard limits, link to `/coop/settings`
7. Approve a Recommendation — approve/reject flow, link to `/recommendations`
8. You're All Set — daily checklist (Home, Coop, Recommendations tabs), tips, restart link

**Test file** (`tutorial.test.ts`) — 7 Vitest tests:
- Step 3 "I did this" writes `tutorial_step=4` to localStorage
- Step 3 "I did this" calls `goto('/tutorial/4')`
- Step 8 "Finish" sets `tutorial_completed='true'`
- Step 8 "Finish" removes `tutorial_step`
- Step 8 "Finish" does NOT call `goto('/tutorial/9')`
- Step 4 renders back link with `href="/tutorial/3"`
- Step 5 renders its button regardless of `tutorial_step` value in localStorage

### Task 2: Welcome Banner + Settings Tutorial Tab

**Root layout** (`+layout.svelte`) additions:
- `let showTutorialBanner = $state(false)` alongside existing `$state` variables
- `dismissWelcome()` sets `tutorial_welcome_dismissed='true'` and hides banner
- `onMount` gate: `!tutorial_completed && !tutorial_welcome_dismissed` → `showTutorialBanner = true`
- Banner markup with `role="banner"`, text, "Start Tutorial" link to `/tutorial/1`, "Skip" button
- Banner CSS using `color-mix()` for tinted accent background

**Settings layout** — `Tutorial` tab appended to existing `tabs` array, `href='/tutorial/1'` (routes outside settings; tutorial's own redirect handles resume-from-saved-step).

**`.gitignore`** — `site/` added under `# Data / runtime` section (prevents MkDocs build output from being committed in Plan 02).

**README.md** — `tutorial/` entry added to Project Structure routes listing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] jsdom localStorage.clear() not available**
- **Found during:** Task 1 — TDD RED→GREEN phase
- **Issue:** `localStorage.clear is not a function` error; jsdom environment in this vitest config does not expose a writable `clear()` on the global `localStorage` object
- **Fix:** Replaced `localStorage.clear()` in `beforeEach` with `vi.stubGlobal('localStorage', {...})` providing a fresh in-memory store per test; `vi.unstubAllGlobals()` in `afterEach`
- **Files modified:** `hub/dashboard/src/routes/tutorial/tutorial.test.ts`
- **Commit:** eac44af

**2. [Rule 1 - Bug] Dynamic imports caused 5000ms test timeout**
- **Found during:** Task 1 — GREEN phase iteration
- **Issue:** First `await import('./3/+page.svelte')` in a test takes >5000ms for cold Svelte compilation; all other tests use static imports at module top level
- **Fix:** Switched from `await import()` inside each `it()` to static `import Step3 from './3/+page.svelte'` at file top (matches project pattern in all 15 existing test files)
- **Files modified:** `hub/dashboard/src/routes/tutorial/tutorial.test.ts`
- **Commit:** eac44af

**3. [Rule 1 - Bug] screen.getByRole found multiple buttons across test runs**
- **Found during:** Task 1 — GREEN phase iteration
- **Issue:** `screen.getByRole('button', { name: /I did this/i })` found 2 elements when the same describe block rendered the component twice (global `screen` scope across renders)
- **Fix:** Switched to `container.querySelector('button.btn-primary')` using the render-scoped container; matches project test pattern (AlertBar.test.ts, CommandButton.test.ts use container.querySelector)
- **Files modified:** `hub/dashboard/src/routes/tutorial/tutorial.test.ts`
- **Commit:** eac44af

## Known Stubs

None — all tutorial content is complete prose. All localStorage keys are wired to real UI state. No placeholder text or TODO markers in any route file.

## Threat Flags

No new threat surface beyond the plan's threat model. Tutorial pages contain only public documentation text. No new API endpoints, auth paths, or data schema changes introduced.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| All 10 tutorial route files exist | FOUND |
| Task 1 commit eac44af exists | FOUND |
| Task 2 commit f184149 exists | FOUND |
| 16 test files pass, 94 tests pass | PASSED |
