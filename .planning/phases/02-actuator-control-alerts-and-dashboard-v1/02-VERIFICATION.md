---
phase: 02-actuator-control-alerts-and-dashboard-v1
verified: 2026-04-10T19:00:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "POST /api/recommendations/{id}/approve returns 200 and opens the irrigation valve (bridge internal HTTP server on port 8001 proxy — no longer 503)"
    - "POST /api/recommendations/{id}/reject returns 200 and starts the back-off window (same bridge proxy fix)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "PWA install on iOS and Android"
    expected: "Safari on iOS shows 'Add to Home Screen' prompt; Chrome on Android shows 'Install App' banner; installed app opens in standalone portrait mode"
    why_human: "Cannot verify PWA install prompt without a physical device on the local network with HTTPS (requires Caddy running)"
  - test: "Irrigation valve open/close on real hardware"
    expected: "Tapping 'Open valve' in zone detail sends MQTT command, edge node acknowledges, spinner resolves, actuator_state WebSocket delta updates UI to 'open'"
    why_human: "No edge node hardware in test environment; 10s ack timeout would fire 504 without real node"
  - test: "Coop door automation and stuck-door alert"
    expected: "Coop door opens at sunrise + offset, closes at hard close time; if edge node does not ack within 60s, P0 alert appears in alert bar"
    why_human: "Requires real hardware and 24-hour observation cycle"
  - test: "Recommendation approve/reject end-to-end flow"
    expected: "Approve: 200 response, valve opens via MQTT, actuator_state WebSocket delta updates UI, recommendation card disappears. Reject: 200 response, card disappears, same recommendation does not re-appear within back-off window."
    why_human: "Requires bridge and API running in Docker with MQTT broker; integration cannot be verified by code inspection alone; requires real sensor data to generate a recommendation."
---

# Phase 2: Actuator Control, Alerts, and Dashboard V1 — Verification Report

**Phase Goal:** The farmer can monitor all garden zones, manually control irrigation and the coop door, and act on rule-based recommendations from the recommend-and-confirm queue — all from a mobile-friendly PWA. This phase delivers the product's core UX differentiator; the recommendation engine is rule-based for now, but the approve/reject flow is production-quality and sets the pattern for Phase 4.
**Verified:** 2026-04-10T19:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plan 02-07)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A POST to /api/actuators/irrigate publishes an MQTT command and waits up to 10s for ack | VERIFIED | actuator_router.py: `asyncio.wait_for(ack_event.wait(), timeout=ACK_TIMEOUT_SECONDS)` at line 85; 409 for second open at line 107; 504 on timeout |
| 2 | Hub rejects a second irrigation command while one zone is already open (409) | VERIFIED | `active_irrigation_zone` module-level var; guard at line 105 returns 409 |
| 3 | Rule engine emits recommendation when VWC drops below zone threshold | VERIFIED | rule_engine.py: evaluate_zone() checks `value >= low_threshold`; returns rec dict when below |
| 4 | Duplicate recommendations suppressed; rejected recs trigger back-off window | VERIFIED | RuleEngine._recommendations dict; pending guard at line 46; backoff guard at lines 49-57; all 7 rule engine tests pass |
| 5 | Alerts fire on threshold crossing and clear only past hysteresis | VERIFIED | AlertEngine.evaluate() with HYSTERESIS_BANDS; 14 alert engine tests pass |
| 6 | POST /api/recommendations/{id}/approve opens the irrigation valve AND starts sensor-feedback loop | VERIFIED | recommendation_router.py proxies via aiohttp.ClientSession to http://bridge:8001/internal/recommendations/{id}/approve; bridge _handle_approve calls rule_engine.approve(), publishes aiomqtt valve-open command, calls irrigation_loop.start(zone_id, target_vwc); no 503 guard in API handler body |
| 7 | POST /api/recommendations/{id}/reject starts back-off window | VERIFIED | recommendation_router.py proxies to http://bridge:8001/internal/recommendations/{id}/reject; bridge _handle_reject calls rule_engine.reject() which activates the back-off window |

**Score: 7/7 truths verified**

## Re-verification: Gap Closure Assessment

### Previous Gaps

**Gap 1: approve/reject always returned HTTP 503**

Root cause (confirmed in initial verification): API and bridge are separate Docker processes. `RuleEngine` and `IrrigationLoop` live in bridge. `recommendation_router.init()` in API receives `rule_engine=None`, causing the 503 guard to fire on every call.

**Fix delivered by plan 02-07:**

- `hub/bridge/main.py`: Added `from aiohttp import web` at top-level imports. Added `_bridge_read_vwc_high_threshold()`, `_handle_approve()`, `_handle_reject()`, and `run_internal_server()` functions. Updated `asyncio.gather()` to include `run_internal_server(db_pool)`. Bridge now binds `aiohttp.web.Application` to `0.0.0.0:8001` with two POST routes.
- `hub/api/recommendation_router.py`: Completely replaced handler bodies. Approve and reject now proxy to `BRIDGE_INTERNAL_URL` (default `http://bridge:8001`) via `aiohttp.ClientSession`. The `_rule_engine` 503 guard is gone from both handler bodies. `init()` signature preserved — `hub/api/main.py` requires no changes.
- `hub/api/requirements.txt`: `aiohttp==3.11.16` added.
- `hub/docker-compose.yml`: `bridge` service gained `expose: ["8001"]` (Docker-internal; not host-bound). `api` service `depends_on` now includes `bridge`.

**Verification of fix:**

| Check | Result |
|-------|--------|
| `python3 -c "import ast; ast.parse(open('hub/bridge/main.py').read())"` | OK |
| `python3 -c "import ast; ast.parse(open('hub/api/recommendation_router.py').read())"` | OK |
| `grep -q "_handle_approve" hub/bridge/main.py` | OK |
| `grep -q "_handle_reject" hub/bridge/main.py` | OK |
| `grep -q "run_internal_server" hub/bridge/main.py` | OK (defined at line 352; called at line 465 in asyncio.gather) |
| `grep -c "8001" hub/bridge/main.py` | 4 occurrences |
| `grep -q "BRIDGE_INTERNAL_URL" hub/api/recommendation_router.py` | OK |
| `grep -q "aiohttp.ClientSession" hub/api/recommendation_router.py` | OK |
| `grep "if not _rule_engine" hub/api/recommendation_router.py` | No output — guard removed |
| `grep -q "aiohttp" hub/api/requirements.txt` | OK (aiohttp==3.11.16) |
| `grep -q "expose" hub/docker-compose.yml` | OK |
| `grep -q "8001" hub/docker-compose.yml` | OK |
| bridge expose in docker-compose | `['8001']` |
| api depends_on in docker-compose | `['timescaledb', 'bridge']` |
| `rule_engine.approve()` called in bridge _handle_approve | Line 291 |
| `rule_engine.reject()` called in bridge _handle_reject | Line 341 |
| `irrigation_loop.start(zone_id, target_vwc)` called in _handle_approve | Line 322 |
| Rollback: `rule_engine.reject(recommendation_id)` called if MQTT publish fails | Line 318 |
| Bridge pytest (55 tests) | 55 passed in 0.21s |
| Dashboard npm test (45 tests) | 45 passed in 6.14s |

**Gap 2 (same root cause):** Resolved by same fix.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hub/api/actuator_router.py` | REST endpoints for irrigation and coop door commands | VERIFIED | Both POST /api/actuators/irrigate and POST /api/actuators/coop-door exist |
| `hub/bridge/models.py` | Pydantic models for ActuatorCommand, ActuatorAck, AlertModel, RecommendationModel | VERIFIED | All 4 classes present |
| `hub/bridge/zone_config.py` | ZoneConfigStore with env-var defaults | VERIFIED | ZoneConfigStore and ZoneConfig classes; VWC_LOW_DEFAULT at line 13 |
| `hub/bridge/rule_engine.py` | RuleEngine with evaluate_zone, approve, reject, backoff, cooldown | VERIFIED | All methods present; all 12 tests pass |
| `hub/bridge/alert_engine.py` | AlertEngine with hysteresis evaluation and state grouping | VERIFIED | All methods present; all 14 tests pass |
| `hub/bridge/health_score.py` | compute_health_score function | VERIFIED | Function exists; returns green/yellow/red dict |
| `hub/bridge/irrigation_loop.py` | IrrigationLoop with check_reading | VERIFIED | Class and check_reading present |
| `hub/bridge/coop_scheduler.py` | NOAA astronomical clock with get_today_schedule and stuck-door watchdog | VERIFIED | get_today_schedule, mark_coop_ack_received, _stuck_door_watchdog all present; 4 tests pass |
| `hub/bridge/main.py` | aiohttp internal HTTP server on port 8001 with approve/reject handlers | VERIFIED | _handle_approve, _handle_reject, run_internal_server present; run_internal_server in asyncio.gather; binds 0.0.0.0:8001 |
| `hub/api/history_router.py` | GET endpoint with TimescaleDB time_bucket query | VERIFIED | time_bucket query at line 16; parameterized; 30m/2h bucket intervals |
| `hub/api/recommendation_router.py` | Approve/reject endpoints proxying to bridge | VERIFIED | Proxies to BRIDGE_INTERNAL_URL via aiohttp.ClientSession; no 503 guard; init() signature preserved |
| `hub/api/requirements.txt` | aiohttp dependency | VERIFIED | aiohttp==3.11.16 present |
| `hub/docker-compose.yml` | bridge expose 8001; api depends_on bridge | VERIFIED | expose: ["8001"] on bridge; api depends_on: [timescaledb, bridge] |
| `hub/dashboard/src/lib/types.ts` | All Phase 2 TypeScript delta types | VERIFIED | AlertEntry, Recommendation, ActuatorStateDelta, ZoneHealthScoreDelta, FeedLevelDelta, WaterLevelDelta, CoopScheduleDelta, extended DashboardSnapshot, expanded WSMessage union |
| `hub/dashboard/src/lib/ws.svelte.ts` | Extended WebSocket store with Phase 2 delta handlers | VERIFIED | 7 $state fields; handlers for all Phase 2 delta types |
| `hub/dashboard/src/lib/TabBar.svelte` | Bottom navigation component | VERIFIED | aria-label="Main navigation"; aria-current; 3 tabs |
| `hub/dashboard/src/lib/AlertBar.svelte` | Persistent alert bar | VERIFIED | role="alert"; goto(alert.deep_link); count badge |
| `hub/dashboard/src/lib/Toast.svelte` | Error toast with auto-dismiss | VERIFIED | setTimeout 5000ms; role="alert"; aria-live="assertive" |
| `hub/dashboard/src/lib/CommandButton.svelte` | Spinner + disabled command button | VERIFIED | aria-disabled; aria-busy; approve/reject variants |
| `hub/dashboard/src/lib/HealthBadge.svelte` | Zone health badge | VERIFIED | GOOD/WARN/CRIT labels; aria-label per score |
| `hub/dashboard/src/lib/SensorChart.svelte` | uPlot time-series chart | VERIFIED | import uPlot; requestAnimationFrame; ResizeObserver; fetch /api/zones/history |
| `hub/dashboard/src/lib/RecommendationCard.svelte` | Recommendation card with approve/reject | VERIFIED | fetch /api/recommendations/{id}/approve and /reject; farm:toast on error; Approve and Reject buttons |
| `hub/dashboard/src/lib/CoopPanel.svelte` | Coop door, feed, water display | VERIFIED | door state with color mapping; schedule display; feed/water progress bars |
| `hub/dashboard/src/routes/zones/[id]/+page.svelte` | Zone detail with irrigation and charts | VERIFIED | SensorChart x3; Open/Close valve buttons; api/actuators/irrigate |
| `hub/dashboard/src/routes/coop/+page.svelte` | Full coop page | VERIFIED | CoopPanel delegate (not stub) |
| `hub/dashboard/src/routes/recommendations/+page.svelte` | Recommendation queue | VERIFIED | RecommendationCard list; "No recommendations" empty state |
| `hub/dashboard/src/service-worker.ts` | PWA service worker | VERIFIED | $service-worker import; farm-${version} cache; /api/ and /ws/ excluded |
| `hub/dashboard/static/manifest.webmanifest` | PWA manifest | VERIFIED | start_url, display: standalone, orientation: portrait |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| hub/api/actuator_router.py | MQTT broker | aiomqtt publish to farm/{node_id}/commands/irrigate | VERIFIED | `client.publish(f"farm/{request.zone_id}/commands/irrigate", ...)` |
| hub/bridge/main.py | hub/api/actuator_router.py | ack forwarded through /internal/notify as actuator_ack; resolve_ack() called | VERIFIED | farm/+/ack/# subscription; /ack/ handler routes to notify_api; main.py lines 91-93 |
| hub/bridge/rule_engine.py | hub/bridge/zone_config.py | RuleEngine reads ZoneConfig thresholds | VERIFIED | zone_config.get(zone_id) called in _evaluate_phase2() |
| hub/bridge/alert_engine.py | WebSocket broadcast | Returns alert_state delta dict for broadcast | VERIFIED | alert_engine.get_alert_state() called in _evaluate_phase2(); broadcast via notify_api |
| hub/bridge/coop_scheduler.py | MQTT broker | Publishes farm/coop/commands/coop_door at scheduled times | VERIFIED | `client.publish("farm/coop/commands/coop_door", ...)` in publish_coop_command() |
| hub/bridge/coop_scheduler.py | hub/bridge/alert_engine.py | _stuck_door_watchdog fires stuck_door:coop P0 alert | VERIFIED | watchdog calls notify_callback with stuck_door:coop |
| hub/api/recommendation_router.py | hub/bridge/main.py | HTTP POST to http://bridge:8001/internal/recommendations/{id}/approve | VERIFIED | aiohttp.ClientSession POST to BRIDGE_INTERNAL_URL; no 503 guard |
| hub/bridge/main.py | hub/bridge/rule_engine.py | _handle_approve calls rule_engine.approve(rec_id) | VERIFIED | Line 291: zone_id = rule_engine.approve(recommendation_id) |
| hub/bridge/main.py | hub/bridge/irrigation_loop.py | approve handler calls irrigation_loop.start(zone_id, target_vwc) | VERIFIED | Line 322: irrigation_loop.start(zone_id, target_vwc) |
| hub/bridge/main.py | hub/bridge/rule_engine.py | _handle_reject calls rule_engine.reject(rec_id) | VERIFIED | Line 341: rule_engine.reject(recommendation_id) |
| hub/dashboard/src/lib/AlertBar.svelte | SvelteKit router | goto() on alert row tap | VERIFIED | `onclick={() => goto(alert.deep_link)}` |
| hub/dashboard/src/lib/ws.svelte.ts | hub/dashboard/src/lib/types.ts | Imports Phase 2 delta types | VERIFIED | AlertEntry, Recommendation, HealthScore, CoopSchedule imported |
| hub/dashboard/src/lib/SensorChart.svelte | /api/zones/{zone_id}/history | fetch in onMount | VERIFIED | `fetch('/api/zones/${zoneId}/history?sensor_type=${sensorType}&days=${days}')` |
| hub/dashboard/src/routes/zones/[id]/+page.svelte | /api/actuators/irrigate | fetch on Open/Close valve button click | VERIFIED | `fetch('/api/actuators/irrigate', ...)` |
| hub/dashboard/src/routes/recommendations/+page.svelte | /api/recommendations | fetch on approve/reject click | VERIFIED | `fetch('/api/recommendations/${recommendation.recommendation_id}/approve', ...)` in RecommendationCard |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| hub/dashboard/src/lib/AlertBar.svelte | alerts (from dashboardStore) | dashboardStore.alerts populated from WebSocket alert_state delta; bridge calls alert_engine.get_alert_state() after each sensor write | Yes — bridge evaluates thresholds on every sensor reading | FLOWING |
| hub/dashboard/src/lib/SensorChart.svelte | chart data | fetch /api/zones/{zone_id}/history -> TimescaleDB time_bucket query on sensor_readings | Yes — parameterized SQL with time_bucket(); BAD quality excluded | FLOWING |
| hub/dashboard/src/lib/RecommendationCard.svelte | recommendation data + approve/reject actions | dashboardStore.recommendations from WebSocket recommendation_queue delta; approve/reject proxy to bridge:8001 which calls real rule_engine + aiomqtt publish | Yes — threshold evaluation and MQTT publish are real; bridge broadcasts updated queue after action | FLOWING |
| hub/dashboard/src/lib/CoopPanel.svelte | doorState, feedLevel, waterLevel, coopSchedule | dashboardStore.actuatorStates, feedLevel, waterLevel, coopSchedule from WebSocket deltas broadcast by bridge | Yes — coop scheduler broadcasts coop_schedule; bridge computes feed/water percentages from sensor values | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Bridge Python tests (rule engine, alert engine, coop scheduler) | `cd hub/bridge && python3 -m pytest tests/ -q` | 55 passed in 0.21s | PASS |
| Frontend component tests | `cd hub/dashboard && npm test -- --run` | 45 tests in 7 files passed | PASS |
| Dashboard production build | `cd hub/dashboard && npm run build` | Exits 0 (not re-run; no dashboard changes in plan 07) | PASS |
| Bridge syntax check | `python3 -c "import ast; ast.parse(open('hub/bridge/main.py').read())"` | OK | PASS |
| API router syntax check | `python3 -c "import ast; ast.parse(open('hub/api/recommendation_router.py').read())"` | OK | PASS |
| Bridge exposes port 8001 in docker-compose | yaml parse: bridge expose == ['8001'] | Confirmed | PASS |
| API depends_on bridge | yaml parse: api depends_on includes 'bridge' | Confirmed | PASS |
| Approve handler calls irrigation_loop.start | `grep "irrigation_loop.start" hub/bridge/main.py` | Line 322 confirmed | PASS |
| 503 guard removed from API router | `grep "if not _rule_engine" hub/api/recommendation_router.py` | No output — removed | PASS |

### Requirements Coverage

| Requirement | Description | Plan | Status | Evidence |
|-------------|-------------|------|--------|----------|
| ZONE-05 | 7-day and 30-day sensor history graphs per zone | 02-03, 02-05 | VERIFIED | history_router.py time_bucket query; SensorChart.svelte fetches and renders |
| ZONE-06 | Composite health score (green/yellow/red) | 02-02, 02-04 | VERIFIED | compute_health_score() in health_score.py; ZoneHealthScoreDelta broadcast; HealthBadge renders |
| IRRIG-01 | Manual irrigation control per zone (hub -> MQTT -> edge) | 02-01 | VERIFIED | POST /api/actuators/irrigate publishes MQTT; zone detail has Open/Close valve buttons |
| IRRIG-02 | Single-zone-at-a-time invariant | 02-01, 02-06 | VERIFIED | active_irrigation_zone module var; 409 guard; recommendation_router also checks |
| IRRIG-04 | Threshold-based irrigation recommendations in queue | 02-02 | VERIFIED | RuleEngine.evaluate_zone() generates recs; displayed in recommendations page |
| IRRIG-05 | Sensor-feedback irrigation loop | 02-02, 02-03, 02-07 | VERIFIED | IrrigationLoop.start() called from bridge _handle_approve after approve; irrigation_loop.check_reading() monitors VWC and stops on target reached or timeout |
| IRRIG-06 | Cool-down window suppresses re-recommendations | 02-02 | VERIFIED | COOLDOWN_MINUTES env var; _last_irrigated dict in RuleEngine |
| COOP-01 | Coop door opens at sunrise, closes at sunset | 02-03 | VERIFIED | coop_scheduler.py; get_today_schedule() uses astral; OPEN_OFFSET, CLOSE_OFFSET env vars |
| COOP-02 | Hard time limit backstop | 02-03 | VERIFIED | min(close_time, hard_close) in get_today_schedule(); COOP_HARD_CLOSE_HOUR env var |
| COOP-03 | Limit switch confirmation; P0 alert if no ack within 60s | 02-03 | VERIFIED | _stuck_door_watchdog() fires P0 alert; mark_coop_ack_received() called in bridge on ack |
| COOP-05 | Dashboard shows coop door state with manual override | 02-04, 02-05 | VERIFIED | CoopPanel shows door state; Open door / Close door CommandButtons |
| COOP-06 | Feed level sensor display with alert | 02-04, 02-05 | VERIFIED | CoopPanel feed progress bar with threshold coloring; FeedLevelDelta from bridge |
| COOP-07 | Water level monitoring with alert | 02-04, 02-05 | VERIFIED | CoopPanel water progress bar; WaterLevelDelta from bridge |
| AI-01 | Recommendation queue UI with approve/reject | 02-03, 02-05, 02-07 | VERIFIED | Recommendation queue renders correctly; approve/reject proxy to bridge:8001 — no longer 503; cards display action_description, sensor_reading, explanation |
| AI-02 | Rule-based recommendation engine | 02-02 | VERIFIED | RuleEngine generates threshold-based irrigation recommendations |
| AI-04 | Recommendation deduplication | 02-02 | VERIFIED | Pending recommendation suppresses re-generation; tests pass |
| AI-05 | Rejection back-off window | 02-02, 02-07 | VERIFIED | Back-off logic in RuleEngine correct; reject endpoint now proxies to bridge — rule_engine.reject() is called; back-off window activates from dashboard rejection |
| UI-02 | Persistent P0/P1 alert bar on all screens | 02-04 | VERIFIED | AlertBar in +layout.svelte; rendered on all routes |
| UI-03 | Alert bar items tappable, route to relevant screen | 02-04 | VERIFIED | goto(alert.deep_link) in AlertBar; deep_link set per alert type in AlertEngine |
| UI-05 | PWA installable on iOS and Android | 02-06 | VERIFIED (code) | service-worker.ts with $service-worker; manifest.webmanifest with standalone/portrait; build succeeds |
| UI-06 | Mobile-first responsive layout | 02-04 | VERIFIED | fixed bottom tab bar; safe-area-inset-bottom; min-height: 44px touch targets; responsive chart heights |
| NOTF-01 | In-app alerts for low moisture, pH, feed/water, stuck door, offline | 02-02 | VERIFIED | AlertEngine evaluates all sensor types; alert_state broadcast on every reading change |
| NOTF-02 | Alert debounce and hysteresis | 02-02 | VERIFIED | HYSTERESIS_BANDS dict; fires on crossing, clears only past hysteresis band; 14 tests pass |

**Orphaned requirements:** None. All 23 requirement IDs listed in the phase requirement set are accounted for in plans 02-01 through 02-07.

**Note:** IRRIG-03 (normally-closed solenoids — procurement requirement) and COOP-04 (linear actuator procurement) are Phase 1 requirements per REQUIREMENTS.md traceability table and are not in the Phase 2 requirement set.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| hub/dashboard/src/lib/ZoneCard.svelte | 55 | `role="button"` on `<section>` element (non-interactive element assigned interactive role) | WARNING | Svelte a11y warning emitted during test run; `<section>` should be `<div>` or a proper `<button>`; does not block functionality |

No new anti-patterns introduced by plan 02-07. The 503-gap blocker from the initial verification is closed.

### Human Verification Required

#### 1. PWA Install on iOS and Android

**Test:** Open https://[hub-ip] (via Caddy HTTPS) in Safari on iPhone and Chrome on Android. Tap the share button on iOS and look for "Add to Home Screen". On Android, look for Chrome install banner. Install the app and verify it opens in standalone portrait mode.
**Expected:** App launches without browser chrome; "Farm Dashboard" as the title; dark theme background (#0f1117).
**Why human:** Cannot verify PWA install prompt programmatically; requires physical device on local network with HTTPS via Caddy.

#### 2. Irrigation Valve Control with Real Edge Node

**Test:** On zone detail page, tap "Open valve". Observe spinner during in-flight state. Confirm edge node opens the physical valve and sends MQTT ack. Verify spinner resolves and zone shows irrigating state.
**Expected:** Spinner shows for up to 10s. If ack received: valve opens, UI updates. If no ack: 504 toast appears.
**Why human:** No edge node hardware in CI; 10s ack timeout fires without real MQTT subscriber.

#### 3. Coop Door Automation and Stuck-Door Alert

**Test:** Observe coop door automation over a sunrise/sunset cycle. Verify door opens at sunrise + offset and closes at min(sunset + offset, hard close). Disable (unplug) limit switch ack and verify a P0 alert appears in the alert bar within 60 seconds of a door command.
**Expected:** Door operates on NOAA-computed schedule; P0 stuck-door alert fires and is visible in the persistent alert bar.
**Why human:** Requires real hardware and 24-hour observation cycle.

#### 4. Recommendation Approve/Reject Flow (End-to-End in Docker)

**Test:** Run `docker compose up` in hub/. Inject a low-VWC sensor reading to the MQTT broker so the rule engine generates a recommendation. Verify the recommendation card appears on the dashboard. Tap Approve. Verify: (a) bridge internal server receives the POST on port 8001, (b) bridge publishes MQTT valve-open command, (c) bridge starts IrrigationLoop, (d) recommendation card disappears from the dashboard. Tap Reject on another recommendation; verify card disappears and the same recommendation does not re-appear for at least RECOMMENDATION_BACKOFF_MINUTES.
**Expected:** Approve returns 200 body `{"status": "approved", "zone_id": ..., "target_vwc": ...}`. Reject returns 200 body `{"status": "rejected"}`. Both bridge and API processes must be running for this flow.
**Why human:** Requires bridge and API running as separate Docker containers with live MQTT broker. Code inspection confirms the wiring is correct; integration test with real Docker network cannot be performed by static analysis.

### Gaps Summary

All automated verification gaps from the initial verification (02-VERIFICATION.md, status: gaps_found) have been closed by plan 02-07. The cross-process 503 dead-end was resolved by:

1. Adding an `aiohttp.web` internal HTTP server to the bridge (`run_internal_server`, port 8001) with `_handle_approve` and `_handle_reject` handlers that call the in-process `rule_engine` and `irrigation_loop` instances directly.
2. Replacing the API's direct `rule_engine` calls (which were always `None`) with HTTP proxy calls to the bridge via `aiohttp.ClientSession`.
3. Wiring `hub/docker-compose.yml` to expose port 8001 on the bridge service (Docker-internal only) and add `bridge` to the API's `depends_on`.

The 55 bridge tests and 45 dashboard tests all continue to pass. No regressions introduced.

Remaining items are in the human verification queue: PWA install on device, real edge node hardware tests, coop door 24-hour cycle, and end-to-end Docker integration of the approve/reject flow.

---

_Verified: 2026-04-10T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — initial gaps closed by plan 02-07_
