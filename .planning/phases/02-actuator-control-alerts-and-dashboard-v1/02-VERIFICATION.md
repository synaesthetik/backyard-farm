---
phase: 02-actuator-control-alerts-and-dashboard-v1
verified: 2026-04-09T12:20:00Z
status: gaps_found
score: 5/7 must-haves verified
re_verification: false
gaps:
  - truth: "POST /api/recommendations/{id}/approve opens irrigation valve AND starts sensor-feedback loop"
    status: failed
    reason: "approve_recommendation() guards on `if not _rule_engine: raise 503`. API startup calls rec_router_module.init(rule_engine=None, irrigation_loop=None) because bridge and API are separate Docker processes — the RuleEngine instance lives exclusively in the bridge process. Every call to /approve or /reject returns HTTP 503. The IrrigationLoop is also None, so even if the guard were bypassed, the sensor-feedback loop would not start."
    artifacts:
      - path: "hub/api/main.py"
        issue: "Lines 58-59: rule_engine=None, irrigation_loop=None passed to init() with comment acknowledging the problem but no resolution"
      - path: "hub/api/recommendation_router.py"
        issue: "Lines 56-57: guard raises 503 when _rule_engine is None — always true in the API process"
    missing:
      - "A bridge-side recommendation approve/reject handler that receives action via /internal/notify and forwards to the in-process RuleEngine"
      - "An API-side proxy endpoint that relays approve/reject to the bridge (e.g., via an internal HTTP call or dedicated MQTT topic)"
      - "OR: consolidate RuleEngine into the API process alongside the actuator router (design change)"

  - truth: "POST /api/recommendations/{id}/reject starts back-off window"
    status: failed
    reason: "Same root cause as approve: _rule_engine is None in the API process. reject_recommendation() guards on `if not _rule_engine: raise 503`."
    artifacts:
      - path: "hub/api/recommendation_router.py"
        issue: "Lines 97-98: guard raises 503 — _rule_engine is always None in API process"
    missing:
      - "Same fix as approve gap above — approve and reject share the same architectural mismatch"
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
---

# Phase 2: Actuator Control, Alerts, and Dashboard V1 — Verification Report

**Phase Goal:** The farmer can monitor all garden zones, manually control irrigation and the coop door, and act on rule-based recommendations from the recommend-and-confirm queue — all from a mobile-friendly PWA.
**Verified:** 2026-04-09T12:20:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A POST to /api/actuators/irrigate publishes an MQTT command and waits up to 10s for ack | VERIFIED | actuator_router.py: `asyncio.wait_for(ack_event.wait(), timeout=ACK_TIMEOUT_SECONDS)` at line 85; 409 for second open at line 107; 504 on timeout |
| 2 | Hub rejects a second irrigation command while one zone is already open (409) | VERIFIED | `active_irrigation_zone` module-level var; guard at line 105 returns 409 |
| 3 | Rule engine emits recommendation when VWC drops below zone threshold | VERIFIED | rule_engine.py: evaluate_zone() checks `value >= low_threshold`; returns rec dict when below |
| 4 | Duplicate recommendations suppressed; rejected recs trigger back-off window | VERIFIED | RuleEngine._recommendations dict; pending guard at line 46; backoff guard at lines 49-57; all 7 rule engine tests pass |
| 5 | Alerts fire on threshold crossing and clear only past hysteresis | VERIFIED | AlertEngine.evaluate() with HYSTERESIS_BANDS; 14 alert engine tests pass |
| 6 | POST /api/recommendations/{id}/approve opens the irrigation valve AND starts sensor-feedback loop | FAILED | approve_recommendation() calls `if not _rule_engine: raise HTTPException(status_code=503)`. API startup passes rule_engine=None — RuleEngine lives in bridge process (separate Docker container). Approve is always 503. |
| 7 | POST /api/recommendations/{id}/reject starts back-off window | FAILED | Same root cause: _rule_engine=None in API process. Reject is always 503. |

**Score: 5/7 truths verified**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hub/api/actuator_router.py` | REST endpoints for irrigation and coop door commands | VERIFIED | Both POST /api/actuators/irrigate and POST /api/actuators/coop-door exist; _send_irrigation_command extracted as shared function |
| `hub/bridge/models.py` | Pydantic models for ActuatorCommand, ActuatorAck, AlertModel, RecommendationModel | VERIFIED | All 4 classes at lines 43, 52, 59, 70 |
| `hub/bridge/zone_config.py` | ZoneConfigStore with env-var defaults | VERIFIED | ZoneConfigStore and ZoneConfig classes present; VWC_LOW_DEFAULT at line 13 |
| `hub/bridge/rule_engine.py` | RuleEngine with evaluate_zone, approve, reject, backoff, cooldown | VERIFIED | All methods present; all 12 tests pass |
| `hub/bridge/alert_engine.py` | AlertEngine with hysteresis evaluation and state grouping | VERIFIED | All methods present; all 14 tests pass |
| `hub/bridge/health_score.py` | compute_health_score function | VERIFIED | Function exists; returns green/yellow/red dict |
| `hub/bridge/irrigation_loop.py` | IrrigationLoop with check_reading | VERIFIED | Class and check_reading present |
| `hub/bridge/coop_scheduler.py` | NOAA astronomical clock with get_today_schedule and stuck-door watchdog | VERIFIED | get_today_schedule, mark_coop_ack_received, _stuck_door_watchdog all present; 4 tests pass |
| `hub/api/history_router.py` | GET endpoint with TimescaleDB time_bucket query | VERIFIED | time_bucket query at line 16; parameterized; 30m/2h bucket intervals |
| `hub/api/recommendation_router.py` | Approve/reject endpoints | PARTIAL | Endpoints exist and are correctly structured; wired with 503-guardrail due to rule_engine=None |
| `hub/dashboard/src/lib/types.ts` | All Phase 2 TypeScript delta types | VERIFIED | AlertEntry, Recommendation, ActuatorStateDelta, ZoneHealthScoreDelta, FeedLevelDelta, WaterLevelDelta, CoopScheduleDelta, extended DashboardSnapshot, expanded WSMessage union (10 types) |
| `hub/dashboard/src/lib/ws.svelte.ts` | Extended WebSocket store with Phase 2 delta handlers | VERIFIED | 7 $state fields; handlers for alert_state, recommendation_queue, actuator_state, zone_health_score, feed_level, water_level, coop_schedule |
| `hub/dashboard/src/lib/TabBar.svelte` | Bottom navigation component | VERIFIED | aria-label="Main navigation"; aria-current; 3 tabs |
| `hub/dashboard/src/lib/AlertBar.svelte` | Persistent alert bar | VERIFIED | role="alert"; goto(alert.deep_link); count badge |
| `hub/dashboard/src/lib/Toast.svelte` | Error toast with auto-dismiss | VERIFIED | setTimeout 5000ms; role="alert"; aria-live="assertive" |
| `hub/dashboard/src/lib/CommandButton.svelte` | Spinner + disabled command button | VERIFIED | aria-disabled; aria-busy; approve/reject variants |
| `hub/dashboard/src/lib/HealthBadge.svelte` | Zone health badge | VERIFIED | GOOD/WARN/CRIT labels; aria-label per score |
| `hub/dashboard/src/lib/SensorChart.svelte` | uPlot time-series chart | VERIFIED | import uPlot; requestAnimationFrame; ResizeObserver; fetch /api/zones/history; "No data for this period" |
| `hub/dashboard/src/lib/RecommendationCard.svelte` | Recommendation card with approve/reject | VERIFIED | fetch /api/recommendations/{id}/approve and /reject; farm:toast on error; Approve and Reject buttons |
| `hub/dashboard/src/lib/CoopPanel.svelte` | Coop door, feed, water display | VERIFIED | door state with color mapping; schedule display; feed/water progress bars with threshold coloring |
| `hub/dashboard/src/routes/zones/[id]/+page.svelte` | Zone detail with irrigation and charts | VERIFIED | SensorChart x3; Open/Close valve buttons; api/actuators/irrigate; Sensor History; 7/30-day toggle |
| `hub/dashboard/src/routes/coop/+page.svelte` | Full coop page | VERIFIED | CoopPanel delegate (not stub) |
| `hub/dashboard/src/routes/recommendations/+page.svelte` | Recommendation queue | VERIFIED | RecommendationCard list; "No recommendations" empty state |
| `hub/dashboard/src/service-worker.ts` | PWA service worker | VERIFIED | $service-worker import; farm-${version} cache; /api/ and /ws/ excluded |
| `hub/dashboard/static/manifest.webmanifest` | PWA manifest | VERIFIED | start_url, display: standalone, orientation: portrait |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| hub/api/actuator_router.py | MQTT broker | aiomqtt publish to farm/{node_id}/commands/irrigate | VERIFIED | `client.publish(f"farm/{request.zone_id}/commands/irrigate", ...)` at line ~70 |
| hub/bridge/main.py | hub/api/actuator_router.py | ack forwarded through /internal/notify as actuator_ack; resolve_ack() called | VERIFIED | `farm/+/ack/#` subscription at line 281; `/ack/` handler at line 292; main.py routes actuator_ack to resolve_ack() at lines 91-93 |
| hub/bridge/rule_engine.py | hub/bridge/zone_config.py | RuleEngine reads ZoneConfig thresholds | VERIFIED | zone_config.get(zone_id) called in bridge/main.py's _evaluate_phase2() before calling rule_engine.evaluate_zone |
| hub/bridge/alert_engine.py | WebSocket broadcast | Returns alert_state delta dict for broadcast | VERIFIED | alert_engine.get_alert_state() called in _evaluate_phase2(); broadcast via notify_api |
| hub/bridge/coop_scheduler.py | MQTT broker | Publishes farm/coop/commands/coop_door at scheduled times | VERIFIED | `client.publish("farm/coop/commands/coop_door", ...)` in publish_coop_command() |
| hub/bridge/coop_scheduler.py | hub/bridge/alert_engine.py | _stuck_door_watchdog fires stuck_door:coop P0 alert via notify_callback | VERIFIED | watchdog calls notify_callback with stuck_door:coop at line 90 |
| hub/api/recommendation_router.py | hub/api/actuator_router.py | approve_recommendation() calls _send_irrigation_command() | PARTIAL | _send_irrigation_command imported and called correctly; BUT blocked by rule_engine=None guard (503) before reaching this line |
| hub/bridge/main.py | hub/bridge/rule_engine.py | Calls rule_engine.evaluate_zone after each sensor write | VERIFIED | rule_engine.evaluate_zone called in _evaluate_phase2() at line 138 |
| hub/bridge/main.py | hub/bridge/alert_engine.py | Calls alert_engine.evaluate after each sensor write | VERIFIED | Multiple alert_engine.evaluate calls at lines 149, 156, 159, 166, 169, 178, 193 |
| hub/dashboard/src/lib/AlertBar.svelte | SvelteKit router | goto() on alert row tap | VERIFIED | `onclick={() => goto(alert.deep_link)}` at line 17 |
| hub/dashboard/src/lib/ws.svelte.ts | hub/dashboard/src/lib/types.ts | Imports Phase 2 delta types | VERIFIED | AlertEntry, Recommendation, HealthScore, CoopSchedule imported |
| hub/dashboard/src/lib/SensorChart.svelte | /api/zones/{zone_id}/history | fetch in onMount | VERIFIED | `fetch('/api/zones/${zoneId}/history?sensor_type=${sensorType}&days=${days}')` at line 77 |
| hub/dashboard/src/routes/zones/[id]/+page.svelte | /api/actuators/irrigate | fetch on Open/Close valve button click | VERIFIED | `fetch('/api/actuators/irrigate', ...)` at line 26 |
| hub/dashboard/src/routes/recommendations/+page.svelte | /api/recommendations | fetch on approve/reject click | VERIFIED | `fetch('/api/recommendations/${recommendation.recommendation_id}/approve', ...)` in RecommendationCard |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| hub/dashboard/src/lib/AlertBar.svelte | alerts (from dashboardStore) | dashboardStore.alerts populated from WebSocket alert_state delta; bridge calls alert_engine.get_alert_state() after each sensor write | Yes — bridge evaluates thresholds on every sensor reading | FLOWING |
| hub/dashboard/src/lib/SensorChart.svelte | chart data | fetch /api/zones/{zone_id}/history -> TimescaleDB time_bucket query on sensor_readings | Yes — parameterized SQL with time_bucket(); BAD quality excluded | FLOWING |
| hub/dashboard/src/lib/RecommendationCard.svelte | recommendation data | dashboardStore.recommendations from WebSocket recommendation_queue delta; bridge rule_engine.get_pending_recommendations() | Yes — real threshold evaluation in bridge | FLOWING (but approve/reject is hollow — see gap) |
| hub/dashboard/src/lib/CoopPanel.svelte | doorState, feedLevel, waterLevel, coopSchedule | dashboardStore.actuatorStates, feedLevel, waterLevel, coopSchedule from WebSocket deltas broadcast by bridge | Yes — coop scheduler broadcasts coop_schedule; bridge computes feed/water percentages from sensor values | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Bridge Python tests (rule engine, alert engine, coop scheduler) | `cd hub/bridge && python3 -m pytest tests/test_rule_engine.py tests/test_alert_engine.py tests/test_coop_scheduler.py -v` | 30 passed in 0.14s | PASS |
| Frontend component tests | `cd hub/dashboard && npm test -- --run` | 45 tests in 7 files passed | PASS |
| Dashboard production build | `cd hub/dashboard && npm run build` | Exits 0, built in 4.25s | PASS |
| TypeScript types include ActuatorStateDelta | `grep -q "ActuatorStateDelta" hub/dashboard/src/lib/types.ts` | Exits 0 | PASS |
| Bridge subscribes to ack topics | `grep "farm/+/ack/#" hub/bridge/main.py` | Line 281 found | PASS |
| Approve endpoint returns 503 with no rule_engine | Verified by code inspection: `rule_engine=None` in init; 503 guard fires | Always 503 in production API process | FAIL |

### Requirements Coverage

| Requirement | Description | Plan | Status | Evidence |
|-------------|-------------|------|--------|----------|
| ZONE-05 | 7-day and 30-day sensor history graphs per zone | 02-03, 02-05 | VERIFIED | history_router.py time_bucket query; SensorChart.svelte fetches and renders |
| ZONE-06 | Composite health score (green/yellow/red) | 02-02, 02-04 | VERIFIED | compute_health_score() in health_score.py; ZoneHealthScoreDelta broadcast; HealthBadge renders |
| IRRIG-01 | Manual irrigation control per zone (hub -> MQTT -> edge) | 02-01 | VERIFIED | POST /api/actuators/irrigate publishes MQTT; zone detail has Open/Close valve buttons |
| IRRIG-02 | Single-zone-at-a-time invariant | 02-01, 02-06 | VERIFIED | active_irrigation_zone module var; 409 guard; recommendation_router also checks |
| IRRIG-04 | Threshold-based irrigation recommendations in queue | 02-02 | VERIFIED | RuleEngine.evaluate_zone() generates recs; displayed in recommendations page |
| IRRIG-05 | Sensor-feedback irrigation loop | 02-02, 02-03 | PARTIAL | IrrigationLoop implementation exists and is correct; but approve endpoint is 503 — valve never opens from recommendation approval flow |
| IRRIG-06 | Cool-down window suppresses re-recommendations | 02-02 | VERIFIED | COOLDOWN_MINUTES env var; _last_irrigated dict in RuleEngine |
| COOP-01 | Coop door opens at sunrise, closes at sunset | 02-03 | VERIFIED | coop_scheduler.py; get_today_schedule() uses astral; OPEN_OFFSET, CLOSE_OFFSET env vars |
| COOP-02 | Hard time limit backstop | 02-03 | VERIFIED | min(close_time, hard_close) at line in get_today_schedule(); COOP_HARD_CLOSE_HOUR env var |
| COOP-03 | Limit switch confirmation; P0 alert if no ack within 60s | 02-03 | VERIFIED | _stuck_door_watchdog() fires P0 alert; mark_coop_ack_received() called in bridge on ack |
| COOP-05 | Dashboard shows coop door state with manual override | 02-04, 02-05 | VERIFIED | CoopPanel shows door state; Open door / Close door CommandButtons |
| COOP-06 | Feed level sensor display with alert | 02-04, 02-05 | VERIFIED | CoopPanel feed progress bar with threshold coloring; FeedLevelDelta from bridge |
| COOP-07 | Water level monitoring with alert | 02-04, 02-05 | VERIFIED | CoopPanel water progress bar; WaterLevelDelta from bridge |
| AI-01 | Recommendation queue UI with approve/reject | 02-03, 02-05 | PARTIAL | Recommendation queue renders correctly; cards display action_description, sensor_reading, explanation; but approve/reject calls return 503 |
| AI-02 | Rule-based recommendation engine | 02-02 | VERIFIED | RuleEngine generates threshold-based irrigation recommendations |
| AI-04 | Recommendation deduplication | 02-02 | VERIFIED | Pending recommendation suppresses re-generation; tests pass |
| AI-05 | Rejection back-off window | 02-02 | PARTIAL | Back-off logic in RuleEngine is correct; but reject endpoint is 503 — back-off never triggers from dashboard |
| UI-02 | Persistent P0/P1 alert bar on all screens | 02-04 | VERIFIED | AlertBar in +layout.svelte; rendered on all routes |
| UI-03 | Alert bar items tappable, route to relevant screen | 02-04 | VERIFIED | goto(alert.deep_link) in AlertBar; deep_link set per alert type in AlertEngine |
| UI-05 | PWA installable on iOS and Android | 02-06 | VERIFIED (code) | service-worker.ts with $service-worker; manifest.webmanifest with standalone/portrait; build succeeds |
| UI-06 | Mobile-first responsive layout | 02-04 | VERIFIED | fixed bottom tab bar; safe-area-inset-bottom; min-height: 44px touch targets; responsive chart heights |
| NOTF-01 | In-app alerts for low moisture, pH, feed/water, stuck door, offline | 02-02 | VERIFIED | AlertEngine evaluates all sensor types; alert_state broadcast on every reading change |
| NOTF-02 | Alert debounce and hysteresis | 02-02 | VERIFIED | HYSTERESIS_BANDS dict; fires on crossing, clears only past hysteresis band; 14 tests pass |

**Orphaned requirements:** None. All 23 requirement IDs listed in the phase requirement set are accounted for in the plans above.

**Note:** IRRIG-03 (normally-closed solenoids — procurement requirement) and COOP-04 (linear actuator procurement) are Phase 1 requirements per REQUIREMENTS.md traceability table and are not in the Phase 2 requirement set.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| hub/api/main.py | 58-59 | `rule_engine=None, irrigation_loop=None` passed to rec_router init with acknowledgment comment | BLOCKER | Approve and reject endpoints always return 503; recommendation queue is display-only; IRRIG-05 and AI-05 not achievable from dashboard |
| hub/dashboard/src/lib/ZoneCard.svelte | 55 | `role="button"` on `<section>` element (non-interactive element assigned interactive role) | WARNING | Svelte a11y warning emitted during test run; `<section>` should be `<div>` or a proper `<button>`; does not block functionality |

### Human Verification Required

#### 1. PWA Install on iOS and Android

**Test:** Open https://[hub-ip] (via Caddy HTTPS) in Safari on iPhone and Chrome on Android. Tap the share button on iOS and look for "Add to Home Screen". On Android, look for Chrome install banner. Install the app and verify it opens in standalone portrait mode.
**Expected:** App launches without browser chrome; "Farm Dashboard" as the title; dark theme background (#0f1117).
**Why human:** Cannot verify PWA install prompt programmatically; requires physical device on local network with HTTPS via Caddy.

#### 2. Irrigation Valve Control with Real Edge Node

**Test:** On zone detail page, tap "Open valve". Observe spinner during in-flight state. Confirm edge node opens the physical valve and sends MQTT ack. Verify spinner resolves and zone shows irrigating state.
**Expected:** Spinner shows for up to 10s. If ack received: valve opens, UI updates. If no ack: 504 toast appears.
**Why human:** No edge node hardware in CI; 10s ack timeout fires without real MQTT subscriber.

#### 3. Recommendation Approve/Reject Flow (After Gap Fix)

**Test:** After the rule_engine wiring gap is resolved, trigger a low-VWC reading so a recommendation appears in the queue. Tap Approve. Verify the valve opens, zone shows irrigating, and the recommendation card disappears. Tap Reject on another recommendation; verify the card disappears and the same recommendation does not re-appear within the back-off window.
**Expected:** Approve: 200 response, actuator_state WebSocket delta updates UI, recommendation_queue delta removes card. Reject: 200 response, card removed, no re-generation for RECOMMENDATION_BACKOFF_MINUTES.
**Why human:** Requires gap fix first; then requires real sensor data and edge node hardware.

### Gaps Summary

**Root cause:** The API and bridge run as **separate Docker processes** (confirmed in hub/docker-compose.yml: `bridge:` and `api:` are independent services). The `RuleEngine` and `IrrigationLoop` instances are instantiated in the bridge process and are inaccessible from the API process. The `recommendation_router.init()` call in `hub/api/main.py` correctly acknowledges this constraint in a comment but passes `None` without providing an alternative mechanism.

This means:
- `POST /api/recommendations/{id}/approve` always returns HTTP 503 ("Rule engine not initialized")
- `POST /api/recommendations/{id}/reject` always returns HTTP 503
- The approve flow's valve-open logic (`_send_irrigation_command`) is never reached
- The IrrigationLoop's sensor-feedback monitoring is never started
- Back-off windows (AI-05) never start from user rejection actions

**Impact on phase goal:** The "act on rule-based recommendations from the recommend-and-confirm queue" portion of the phase goal is not achievable. The recommendation queue displays correctly (bridge broadcasts recommendations via WebSocket), but the farmer cannot approve or reject them from the dashboard.

**What IS working:**
- All rule engine logic (threshold evaluation, dedup, backoff, cooldown) is correct and tested
- Recommendations are generated by the bridge and broadcast to the dashboard
- The recommendation queue UI renders correctly
- Manual irrigation control (direct Open/Close valve without recommendations) works via `POST /api/actuators/irrigate`
- All other Phase 2 goals are delivered: alerts, health scores, coop automation, PWA, sensor history charts

**Recommended fix options:**

Option A (minimal): Add an internal bridge endpoint (or repurpose `/internal/notify`) so the API can proxy approve/reject actions to the bridge. The bridge would apply `rule_engine.approve(rec_id)` and publish the MQTT valve command, then notify the API of the actuator_state change.

Option B (architectural): Move `RuleEngine` and `IrrigationLoop` into the API process (where the recommendation endpoints live). The bridge would continue to broadcast sensor deltas; the API would process them through the rule engine. This requires the API to subscribe to /internal/notify sensor readings and call rule_engine.evaluate_zone.

Option C (queue-based): Introduce an internal MQTT topic (e.g., `farm/internal/recommendations/approve`) that the API publishes to when approve is called, and the bridge subscribes to and handles.

---

_Verified: 2026-04-09T12:20:00Z_
_Verifier: Claude (gsd-verifier)_
