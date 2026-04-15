---
phase: 03-flock-management-and-unified-dashboard
verified: 2026-04-15T00:00:00Z
status: gaps_found
score: 9/12 must-haves verified
gaps:
  - truth: "Egg history endpoint returns actual and expected counts for charting"
    status: failed
    reason: "flock_router.py queries column 'counted_date' but init-db.sql defines it as 'count_date'. Both the SELECT in egg-history and the INSERT in refresh-eggs will fail at runtime with a column-not-found DB error."
    artifacts:
      - path: "hub/api/flock_router.py"
        issue: "Line 305-306: queries 'counted_date' column; line 389: inserts into 'counted_date'. Schema column is 'count_date'."
      - path: "hub/init-db.sql"
        issue: "egg_counts table defines 'count_date DATE PRIMARY KEY' — no 'counted_date' column exists."
    missing:
      - "Rename all references to 'counted_date' in hub/api/flock_router.py to 'count_date' (lines 305, 306, 309, 389, 391)"
      - "Add 'hen_present' column to egg_counts table in hub/init-db.sql OR remove hen_present from the INSERT statement in flock_router.py (the bridge uses count_date and does not insert hen_present)"

  - truth: "Refresh-eggs endpoint triggers immediate egg count estimation"
    status: failed
    reason: "INSERT in refresh-eggs includes columns 'counted_date' and 'hen_present' which do not exist in the egg_counts schema. The endpoint would raise a DB error on every call."
    artifacts:
      - path: "hub/api/flock_router.py"
        issue: "Lines 389-394: INSERT INTO egg_counts (counted_date, estimated_count, hen_present, raw_weight_grams) references two non-existent columns."
      - path: "hub/init-db.sql"
        issue: "egg_counts table has 'count_date' (not 'counted_date') and no 'hen_present' column."
    missing:
      - "Fix INSERT: use 'count_date' for the date column"
      - "Either add 'hen_present BOOLEAN' to the egg_counts schema in init-db.sql, or remove 'hen_present' from the INSERT and ON CONFLICT clause in flock_router.py to match the actual schema"

  - truth: "30-day production trend chart shows actual vs expected as two-series overlay"
    status: failed
    reason: "ProductionChart.svelte expects the API to return { dates: string[], actual: number[], expected: number[] } but the /api/flock/egg-history endpoint returns list[EggHistoryPoint] (array of objects with 'date', 'actual_count', 'expected_count' fields). 'data.dates' will always be undefined, so the chart will always show the 'Not enough data yet' empty state regardless of how much data is in the DB."
    artifacts:
      - path: "hub/dashboard/src/lib/ProductionChart.svelte"
        issue: "Lines 70-72: reads data.dates, data.actual, data.expected — none of these keys exist in the API response. The API returns an array, not an object with these keys."
      - path: "hub/api/flock_router.py"
        issue: "Line 267: returns list[EggHistoryPoint] where each point has fields 'date', 'actual_count', 'expected_count' — not the object shape that ProductionChart expects."
    missing:
      - "Either: (a) update ProductionChart.svelte to map the array response — extract dates[], actual[], expected[] from the returned array of EggHistoryPoint objects; OR (b) change the API response shape to match what ProductionChart expects"
human_verification:
  - test: "Verify Home tab unified overview layout on mobile and desktop"
    expected: "FlockSummaryCard renders at top on mobile, right column on desktop. Compact zone cards render below on mobile, left column on desktop. Tab bar shows 4 tabs with Home highlighted at /"
    why_human: "Visual layout and responsive breakpoint behavior cannot be verified programmatically"
  - test: "Verify HenPresentIndicator pulse animation"
    expected: "When hen_present=true, Egg icon pulses (scale + opacity) at 2s ease-in-out loop. Text 'Hen present' visible in accent color."
    why_human: "CSS animation correctness requires visual inspection"
  - test: "Verify FlockSummaryCard trend indicator resolves percentage once egg-history data flows"
    expected: "After gap closure fixes the ProductionChart API shape mismatch, the trend percentage should eventually appear in FlockSummaryCard. Currently renders a neutral Minus icon — this is a known acknowledged stub from Plan 03-02/03-03."
    why_human: "Expected production is not stored in dashboardStore; the trend indicator always shows Minus/neutral. This was documented as an intentional deferral."
---

# Phase 3: Flock Management and Unified Dashboard — Verification Report

**Phase Goal:** The flock's health story is complete — egg production is tracked against a breed/age/daylight model, feed consumption is derived from load cell data, and production drops trigger alerts. A single overview screen surfaces all garden zones and the flock summary together.

**Verified:** 2026-04-15
**Status:** gaps_found — 3 gaps blocking full goal achievement
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Egg count is estimated from nesting box weight via bridge | VERIFIED | `egg_estimator.estimate_egg_count()` implemented; bridge `_evaluate_phase3_nesting_box()` and `periodic_flock_loop()` call it |
| 2  | Expected production model computes flock_size x breed_lay_rate x age_factor x daylight_factor | VERIFIED | `production_model.py` exports `compute_expected_production`, `compute_age_factor`, `compute_daylight_factor`, `BREED_LAY_RATES` (13 breeds) |
| 3  | Production drop alert fires when 3-day rolling average falls below 75% of expected | VERIFIED | `alert_engine.py` has `production_drop` in HYSTERESIS_BANDS and ALERT_DEFINITIONS; `periodic_flock_loop` evaluates with <3 day guard |
| 4  | Feed consumption rate derived from daily load cell weight delta with refill detection | VERIFIED | `feed_consumption.compute_daily_feed_consumption()` implemented; `daily_feed_loop` queries and stores daily deltas |
| 5  | Flock configuration is persisted in TimescaleDB and retrievable via REST API | VERIFIED | `flock_config` table in schema; `FlockConfigStore` in bridge; `/api/flock/config` GET/PUT endpoints exist |
| 6  | Home tab at / is the default landing page showing all zones and flock summary | VERIFIED | `+page.svelte` at `/` renders `FlockSummaryCard` + compact `ZoneCard` entries from dashboardStore |
| 7  | Zones list has moved from / to /zones and still works | VERIFIED | `hub/dashboard/src/routes/zones/+page.svelte` exists with zone grid + SystemHealthPanel |
| 8  | TabBar shows 4 tabs: Home, Zones, Coop, Recs | VERIFIED | TabBar.svelte has LayoutDashboard/Sprout/Home/Bell tabs; exact-match for Home ('/') |
| 9  | Flock summary card shows door status, egg count, and taps to /coop | VERIFIED | `FlockSummaryCard.svelte` has `role="button"`, `goto('/coop')`, door state badge, egg count from dashboardStore |
| 10 | Egg history endpoint returns actual and expected counts for charting | FAILED | Column name mismatch: API queries `counted_date` but schema has `count_date`; endpoint will throw DB error |
| 11 | Refresh-eggs endpoint triggers immediate egg count estimation | FAILED | INSERT uses `counted_date` (non-existent) and `hen_present` (no column in schema); runtime DB error on every call |
| 12 | 30-day production trend chart shows actual vs expected overlay | FAILED | ProductionChart.svelte reads `data.dates/actual/expected` from API response but API returns array of objects with `date/actual_count/expected_count` fields; chart always shows "Not enough data" |

**Score:** 9/12 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hub/bridge/egg_estimator.py` | `estimate_egg_count(weight, config) -> (count, hen_present)` | VERIFIED | Exists, substantive, wired via bridge main.py |
| `hub/bridge/production_model.py` | `compute_expected_production`, `compute_age_factor`, `compute_daylight_factor`, `BREED_LAY_RATES` | VERIFIED | All 4 exports present and complete |
| `hub/bridge/feed_consumption.py` | `compute_daily_feed_consumption` with refill detection | VERIFIED | Returns (None, True) on refill, (grams, False) on normal day |
| `hub/bridge/flock_config.py` | `FlockConfig` dataclass + `FlockConfigStore` | VERIFIED | Both exported; DB query pattern mirrors zone_config.py |
| `hub/bridge/tests/test_egg_estimator.py` | Unit tests for egg estimation | VERIFIED | 35 total flock tests pass (confirmed by test run) |
| `hub/bridge/tests/test_production_model.py` | Unit tests for production model | VERIFIED | Age factor, daylight factor, expected production tested |
| `hub/bridge/tests/test_feed_consumption.py` | Unit tests for feed consumption | VERIFIED | Refill detection and normal consumption tested |
| `hub/bridge/alert_engine.py` | `production_drop` + `feed_consumption_drop` alerts | VERIFIED | Both in HYSTERESIS_BANDS and ALERT_DEFINITIONS |
| `hub/bridge/main.py` | `periodic_flock_loop` + `daily_feed_loop` in asyncio.gather | VERIFIED | Both functions defined and added to gather at lines 711-712 |
| `hub/api/flock_router.py` | GET/PUT /config, GET /egg-history, POST /refresh-eggs | PARTIAL | Router exists and is mounted, but egg-history and refresh-eggs will fail at runtime due to schema column name mismatch |
| `hub/api/ws_manager.py` | Snapshot includes egg_count and feed_consumption | VERIFIED | `_egg_count` and `_feed_consumption` initialized null, updated by nesting_box and feed_consumption deltas |
| `hub/dashboard/src/lib/FlockSummaryCard.svelte` | Compact flock summary card for Home tab | VERIFIED | role=button, aria-label, goto('/coop'), egg count, door badge |
| `hub/dashboard/src/lib/TabBar.svelte` | 4-tab navigation with LayoutDashboard icon | VERIFIED | 4 tabs, exact match for '/' home |
| `hub/dashboard/src/routes/+page.svelte` | Home tab unified overview with FlockSummaryCard | VERIFIED | Imports and renders FlockSummaryCard + compact ZoneCards |
| `hub/dashboard/src/routes/zones/+page.svelte` | Zones list moved from / | VERIFIED | Exists with full zone grid content |
| `hub/dashboard/src/lib/HenPresentIndicator.svelte` | Animated hen detection indicator | VERIFIED | hen-pulse keyframes, Egg icon, aria-live="polite" |
| `hub/dashboard/src/lib/ProductionChart.svelte` | uPlot two-series chart fetching /api/flock/egg-history | STUB | Exists and uses uPlot, but API response shape mismatch means data never renders — chart always shows empty state |
| `hub/dashboard/src/lib/FeedSparkline.svelte` | Inline SVG 7-day sparkline | VERIFIED | polyline, toPolylinePoints(), division-by-zero guard, aria-hidden |
| `hub/dashboard/src/lib/CoopPanel.svelte` | Extended with egg section, production chart, feed sparkline | VERIFIED | All imports present; HenPresentIndicator, ProductionChart, FeedSparkline wired in |
| `hub/dashboard/src/lib/FlockSettings.svelte` | Flock configuration form | VERIFIED | 11 breeds, breed-conditional lay rate, all validation, tare button, Save PUT |
| `hub/dashboard/src/routes/coop/settings/+page.svelte` | /coop/settings route | VERIFIED | Exists, delegates to FlockSettings |
| `hub/init-db.sql` | flock_config, egg_counts, feed_daily_consumption tables | PARTIAL | All three tables exist, but egg_counts is missing `hen_present` column and uses `count_date` (not `counted_date`) creating a mismatch with flock_router |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `hub/bridge/main.py` | `hub/bridge/egg_estimator.py` | `_evaluate_phase3_nesting_box` calls `estimate_egg_count` | WIRED | Confirmed at line 405 and 441 |
| `hub/bridge/main.py` | `hub/bridge/alert_engine.py` | `periodic_flock_loop` evaluates `production_drop` alert | WIRED | Lines 466-480 query egg_counts and call alert_engine.evaluate |
| `hub/api/main.py` | `hub/api/flock_router.py` | `app.include_router(flock_router.router)` | WIRED | Line 29 in main.py, no prefix (full paths embedded in router decorators) |
| `hub/api/ws_manager.py` | `hub/api/flock_router.py` | Snapshot includes egg_count and feed_consumption from nesting_box/feed_consumption deltas | WIRED | ws_manager.py lines 96-106 handle both delta types |
| `hub/dashboard/src/lib/TabBar.svelte` | `hub/dashboard/src/routes/+page.svelte` | Home tab links to '/' | WIRED | `{ path: '/', label: 'Home' }` |
| `hub/dashboard/src/lib/FlockSummaryCard.svelte` | `/coop` route | `goto('/coop')` on click/keydown | WIRED | Lines 66-73 in FlockSummaryCard.svelte |
| `hub/dashboard/src/routes/+page.svelte` | `hub/dashboard/src/lib/ws.svelte.ts` | reads `dashboardStore.zones` and `dashboardStore.eggCount` (via FlockSummaryCard) | WIRED | dashboardStore imported in +page.svelte; FlockSummaryCard reads eggCount |
| `hub/dashboard/src/lib/CoopPanel.svelte` | `hub/dashboard/src/lib/ws.svelte.ts` | reads `dashboardStore.eggCount` and `dashboardStore.feedConsumption` | WIRED | Lines 69-70 in CoopPanel.svelte |
| `hub/dashboard/src/lib/CoopPanel.svelte` | `/api/flock/refresh-eggs` | Refresh button POSTs | WIRED | Line 77: `fetch('/api/flock/refresh-eggs', { method: 'POST' })` |
| `hub/dashboard/src/lib/CoopPanel.svelte` | `/api/flock/egg-history` | ProductionChart fetches 30-day history | PARTIAL | ProductionChart calls the endpoint, but response shape mismatch means data is never rendered |
| `hub/dashboard/src/lib/FlockSettings.svelte` | `/api/flock/config` | GET on mount, PUT on save | WIRED | onMount fetches GET; handleSave PUTs |
| `hub/dashboard/src/lib/FlockSettings.svelte` | `hub/dashboard/src/lib/ws.svelte.ts` | tare button reads `dashboardStore.eggCount.raw_weight_grams` | WIRED | Line 131: `dashboardStore.eggCount?.raw_weight_grams ?? null` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `FlockSummaryCard.svelte` | `eggCount` (dashboardStore) | WebSocket nesting_box delta → ws_manager → WS broadcast | Yes — flows from bridge via MQTT → periodic_flock_loop | FLOWING (once bridge is processing nesting_box_weight) |
| `ProductionChart.svelte` | `dates`, `actual`, `expected` | `fetch('/api/flock/egg-history?days=30')` | No — API returns array shape, component reads object shape; `data.dates` is always undefined | HOLLOW — wired fetch but data shape mismatch means no data reaches the chart |
| `CoopPanel.svelte` | `feedConsumption` (dashboardStore) | WebSocket feed_consumption delta → ws_manager | Yes — flows from bridge daily_feed_loop | FLOWING |
| `FlockSettings.svelte` | form fields | GET /api/flock/config → DB | Yes — real DB query in flock_router | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Bridge flock unit tests | `cd hub/bridge && python -m pytest tests/test_egg_estimator.py tests/test_production_model.py tests/test_feed_consumption.py -x -q` | 35 passed | PASS |
| egg_estimator exports estimate_egg_count | `python -c "from hub.bridge.egg_estimator import estimate_egg_count"` | Function importable | PASS |
| production_model exports all 4 symbols | File inspection | BREED_LAY_RATES, compute_age_factor, compute_daylight_factor, compute_expected_production all present | PASS |
| flock_router column mismatch | `grep "counted_date" hub/api/flock_router.py` | 5 references to non-existent column | FAIL — runtime DB error |
| ProductionChart API shape | Inspect ProductionChart.svelte vs flock_router.py | Component reads `data.dates/actual/expected`; API returns `[{date, actual_count, expected_count}]` | FAIL — chart always shows empty state |
| ZoneCard compact prop | `grep "compact" hub/dashboard/src/lib/ZoneCard.svelte` | `{#if compact}` branch exists, renders single-row layout | PASS |
| MQTT schema documented | `grep "nesting_box_weight" docs/mqtt-topic-schema.md` | Topic documented | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| FLOCK-01 | 03-01, 03-03, 03-05 | Farmer can enter daily egg count; counts stored per day | VERIFIED | Egg count estimated from nesting box weight (not manual — this is a design decision from Plan 03-01 CONTEXT). Bridge upserts to egg_counts table. |
| FLOCK-02 | 03-01, 03-04, 03-05 | Expected production model: flock_size × breed_lay_rate × age_factor × daylight_hours_factor | VERIFIED | `compute_expected_production()` in production_model.py; FlockSettings configures breed/hatch/size/lighting |
| FLOCK-03 | 03-01, 03-06, 03-05 | Dashboard shows egg production trend chart (actual vs expected) over 30 days | PARTIAL | ProductionChart component exists and uses uPlot but cannot render data due to API/component shape mismatch |
| FLOCK-04 | 03-01 | Production drop alert when 3-day rolling average < 75% of expected | VERIFIED | Alert engine extended; periodic_flock_loop evaluates with guard |
| FLOCK-05 | 03-04, 03-06 | Flock configuration: breed, hatch date, flock size, supplemental lighting | VERIFIED | FlockSettings form with 11 breeds + custom; /coop/settings route; /api/flock/config CRUD |
| FLOCK-06 | 03-01 | Feed consumption tracked from load cell data (daily weight delta) | VERIFIED | `compute_daily_feed_consumption()` + `daily_feed_loop()` + feed_daily_consumption table |
| UI-01 | 03-02, 03-05 | Single overview screen: all garden zones + flock summary in one view | VERIFIED | Home tab at / with FlockSummaryCard + compact ZoneCards from live WS data |

**All 7 Phase 3 requirement IDs are accounted for in the plan frontmatter. No orphaned requirements.**

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `hub/api/flock_router.py` | 305-309 | Queries non-existent column `counted_date` (should be `count_date`) | BLOCKER | egg-history endpoint fails at runtime; chart always shows empty state |
| `hub/api/flock_router.py` | 389-395 | Inserts into non-existent columns `counted_date` and `hen_present` | BLOCKER | refresh-eggs endpoint fails at runtime |
| `hub/dashboard/src/lib/ProductionChart.svelte` | 70-72 | Reads `data.dates`, `data.actual`, `data.expected` from API response that returns an array (no such keys) | BLOCKER | FLOCK-03 production chart never renders data |
| `hub/dashboard/src/lib/FlockSummaryCard.svelte` | 54-63 | Trend indicator always returns `Minus` / neutral — no percentage displayed | WARNING | Trend percentage never shown; acknowledged stub from Plan 03-02/03-03 |

---

## Human Verification Required

### 1. Home Tab Responsive Layout

**Test:** Open dashboard at `/` on a phone-width viewport (~375px) and again at ≥640px desktop width.
**Expected:** Mobile: FlockSummaryCard at top (full width), compact zone cards below. Desktop: 2-column grid with zones left, flock card right.
**Why human:** CSS order/grid behavior and responsive breakpoints cannot be verified by static code analysis.

### 2. HenPresentIndicator Pulse Animation

**Test:** Simulate `hen_present = true` in the store (or have a real sensor reading) and observe the Coop tab.
**Expected:** Egg icon pulses on 2s ease-in-out loop (scale 1→1.15, opacity 1→0.7). "Hen present" text visible in accent color. When `hen_present = false`, indicator completely absent from DOM (not hidden via CSS).
**Why human:** CSS animation timing and conditional DOM rendering require visual confirmation.

### 3. FlockSummaryCard Trend Indicator — Known Stub

**Test:** After gap closure fixes the ProductionChart data flow, verify whether the trend percentage appears in FlockSummaryCard.
**Expected:** FlockSummaryCard always shows `Minus` (neutral) because `expected_production` is never stored in dashboardStore. This is intentional per plans 03-02 and 03-03.
**Why human:** The trend indicator's accuracy depends on whether expected production is ever written back to the store — which neither ProductionChart nor any other component currently does. This is a design limitation acknowledged in both summaries and may require a future plan to resolve.

---

## Gaps Summary

Three gaps block full phase goal achievement:

**Gap 1 and 2 — Schema/API column name mismatch (root cause: same bug):** The `egg_counts` table in `hub/init-db.sql` defines its primary key as `count_date`, but `hub/api/flock_router.py` references this column as `counted_date` in the `GET /api/flock/egg-history` query (lines 305-306, 309) and in the `POST /api/flock/refresh-eggs` INSERT (lines 389-395). Additionally, the INSERT references `hen_present` which is not a column in the schema. At runtime, both endpoints will throw a PostgreSQL `column "counted_date" does not exist` error. The bridge `periodic_flock_loop` correctly uses `count_date` — only the API layer has this mismatch.

**Gap 3 — ProductionChart/API response shape mismatch:** `ProductionChart.svelte` was written expecting the API to return `{ dates: string[], actual: number[], expected: number[] }` (an object with parallel arrays). The actual `/api/flock/egg-history` endpoint returns `list[EggHistoryPoint]` — a JSON array of objects, each with `date`, `actual_count`, `expected_count` fields. Since `data.dates` is always `undefined` on an array, the component treats every response as having zero dates and renders "Not enough data yet — check back in a few days" unconditionally. FLOCK-03 (30-day production trend chart) is blocked until the shape mismatch is resolved.

These three gaps share a single root cause pattern: the API layer (Plan 03-06) diverged from the schema and component contracts established by the other plans. The fixes are mechanical and well-scoped:
- Fix column names in `flock_router.py` (counted_date → count_date)
- Decide whether to add `hen_present` to the DB schema or remove it from the API INSERT
- Fix ProductionChart.svelte to map the array response into the expected parallel-array format

---

_Verified: 2026-04-15_
_Verifier: Claude (gsd-verifier)_
