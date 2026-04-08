---
phase: 01-hardware-foundation-and-sensor-pipeline
verified: 2026-04-08T17:11:31Z
status: gaps_found
score: 12/17 must-haves verified
re_verification: false
gaps:
  - truth: "Dashboard shows live sensor readings per zone with freshness timestamp"
    status: failed
    reason: "WebSocket data routing gap: Caddy routes /ws/dashboard to dashboard:3000 (server.js), which sends only an empty stub snapshot {zones:{}, nodes:{}}. The real WebSocket manager with live data is in FastAPI at api:8000/ws/dashboard, which Caddy never routes to. Browser clients NEVER receive real sensor data."
    artifacts:
      - path: "hub/dashboard/server.js"
        issue: "Handles /ws/dashboard upgrades but sends empty {zones:{}, nodes:{}} snapshot with no connection to real data"
      - path: "hub/Caddyfile"
        issue: "Routes /ws/dashboard to dashboard:3000 (server.js stub) instead of api:8000 (FastAPI ws_manager with real data)"
    missing:
      - "Either: Change Caddyfile to route /ws/dashboard to api:8000 instead of dashboard:3000"
      - "Or: Update server.js to proxy WebSocket connections to api:8000/ws/dashboard"

  - truth: "System health panel shows each node as online/offline with last heartbeat timestamp"
    status: failed
    reason: "Same WebSocket routing gap. The SystemHealthPanel renders correctly from ws.svelte.ts state, but ws.svelte.ts connects to server.js (empty stub), so node state is never populated. The panel will always show 'No nodes connected'."
    artifacts:
      - path: "hub/dashboard/src/lib/ws.svelte.ts"
        issue: "Connects to wss://{host}/ws/dashboard which Caddy proxies to server.js stub, not FastAPI ws_manager"
    missing:
      - "Fix the WebSocket routing (same fix as above resolves this truth)"

  - truth: "WebSocket connection delivers real-time updates without page refresh"
    status: failed
    reason: "WebSocket connection reaches server.js which only delivers one static empty snapshot per connection. No real-time deltas are ever sent."
    artifacts:
      - path: "hub/dashboard/server.js"
        issue: "wss.on('connection') sends one static empty message and no further updates"
    missing:
      - "Fix the WebSocket routing (same fix as above resolves this truth)"

  - truth: "Quality flag badge (GOOD/SUSPECT/BAD) shown inline with each sensor value"
    status: failed
    reason: "UI component (SensorValue.svelte) is fully implemented with quality badge, but data never arrives due to WebSocket routing gap. Dashboard will always show '--' values with no quality badges."
    artifacts:
      - path: "hub/dashboard/src/lib/SensorValue.svelte"
        issue: "Component correctly renders quality badges, but receives null data due to WS routing gap (not a component defect)"
    missing:
      - "Fix the WebSocket routing (same fix as above resolves this truth)"

  - truth: "Stuck sensor indicator appears when a sensor has 30+ consecutive identical values"
    status: failed
    reason: "Same WebSocket routing gap. ZoneCard.svelte correctly renders stuck indicator when sensor.stuck=true, but data never arrives."
    artifacts:
      - path: "hub/dashboard/src/lib/ZoneCard.svelte"
        issue: "Correctly implements stuck indicator but receives no data due to WS routing gap"
    missing:
      - "Fix the WebSocket routing (same fix as above resolves this truth)"

  - truth: "Dashboard unit tests exist for ZoneCard, SensorValue, NodeHealthRow components"
    status: failed
    reason: "plan 01-06 files_modified listed SensorValue.test.ts, ZoneCard.test.ts, NodeHealthRow.test.ts but none of these test files were created. The SUMMARY omits them entirely."
    artifacts:
      - path: "hub/dashboard/src/lib/SensorValue.test.ts"
        issue: "Missing — not created"
      - path: "hub/dashboard/src/lib/ZoneCard.test.ts"
        issue: "Missing — not created"
      - path: "hub/dashboard/src/lib/NodeHealthRow.test.ts"
        issue: "Missing — not created"
    missing:
      - "Create unit tests for SensorValue (quality badge render), ZoneCard (stale/stuck state), NodeHealthRow (ONLINE/OFFLINE status)"

human_verification:
  - test: "HTTPS accessible from LAN browser"
    expected: "Hub dashboard loads over HTTPS without certificate warning on second visit (tls internal with Caddy local CA installed)"
    why_human: "Requires actual hardware running — cannot verify locally; depends on Caddy CA trust installation on client browser"
  - test: "Confirm hub.env credential rotation"
    expected: "MQTT_BRIDGE_PASS in config/hub.env should be CHANGE_ME placeholder, not a real base64-encoded credential"
    why_human: "Real credential I9VDCVWWPH5NkmEWhyc61A== is committed. Rotation requires operator action and .gitignore addition."
---

# Phase 1: Hardware Foundation and Sensor Pipeline — Verification Report

**Phase Goal:** Trustworthy sensor data flows from every edge node to the hub with quality flags, node health is visible on a minimal dashboard, and all hardware failsafes are confirmed before any actuator is connected.
**Verified:** 2026-04-08T17:11:31Z
**Status:** GAPS FOUND
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from Phase Goal + ROADMAP Success Criteria)

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | Live sensor readings appear on dashboard with freshness timestamps | ✗ FAILED | WebSocket routing sends to server.js stub, not FastAPI ws_manager |
| 2  | Readings older than 5 minutes visually flagged as stale | ✗ FAILED | ZoneCard.svelte implements stale logic correctly but no data arrives via WS |
| 3  | Quality flag (GOOD/SUSPECT/BAD) badges shown inline with readings | ✗ FAILED | SensorValue.svelte implements badges but receives no data via WS |
| 4  | Stuck sensor flagged after 30+ consecutive identical values | ✗ FAILED | StuckDetector (bridge) and ZoneCard indicator both work; WS routing breaks delivery |
| 5  | System health panel shows each node as online/offline with last heartbeat | ✗ FAILED | SystemHealthPanel implemented; never populated due to WS routing gap |
| 6  | WebSocket delivers real-time updates without page refresh | ✗ FAILED | WS connects to server.js empty stub, not FastAPI ws_manager |
| 7  | Hub bridge subscribes to farm/+/sensors/# and farm/+/heartbeat | ✓ VERIFIED | bridge/main.py subscribes to both topics |
| 8  | Quality flags applied to every reading based on range checks before DB write | ✓ VERIFIED | apply_quality_flag() called in process_sensor_message(); 18 tests pass |
| 9  | Calibration offsets applied to raw values before DB write | ✓ VERIFIED | CalibrationStore.apply_calibration() called; 4 tests pass |
| 10 | Stuck detection flags sensors with 30+ consecutive identical values | ✓ VERIFIED | StuckDetector.check() called in bridge pipeline; tests pass |
| 11 | Edge node buffers readings in SQLite before MQTT publish; flushes on reconnect | ✓ VERIFIED | buffer.py WAL SQLite, store-before-publish, on_connect flush; 6 tests pass |
| 12 | Edge node polls sensors on configurable interval and publishes via MQTT | ✓ VERIFIED | poll_sensors() in main.py; POLL_INTERVAL_SECONDS configurable |
| 13 | Emergency irrigation shutoff triggers at >= 95% VWC (edge, no hub) | ✓ VERIFIED | LocalRuleEngine.evaluate() with IRRIGATION_SHUTOFF; 9 tests pass |
| 14 | Coop door hard-close triggers at configured hour (edge, no hub) | ✓ VERIFIED | COOP_HARD_CLOSE rule in LocalRuleEngine; tests pass |
| 15 | MQTT broker rejects anonymous connections; per-node ACL enforced | ✓ VERIFIED | allow_anonymous false; acl with per-node write restrictions |
| 16 | TimescaleDB hypertable schema accepts sensor readings with quality/stuck columns | ✓ VERIFIED | init-db.sql has hypertable with quality CHECK and stuck BOOLEAN |
| 17 | Hub dashboard is accessible from LAN via HTTPS | ? HUMAN | Requires running hardware; tls internal configured in Caddyfile |

**Score:** 9/17 truths verified (10 with human item deferred); 6 failed due to WebSocket routing gap + missing tests

---

## Required Artifacts

### Plan 01-01: Hub Service Stack

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hub/docker-compose.yml` | Service stack with 5 services | ✓ VERIFIED | 6 services; ARM64; TimescaleDB localhost-only |
| `hub/Caddyfile` | HTTPS reverse proxy with tls internal | ✓ VERIFIED | tls internal; correct reverse_proxy rules |
| `hub/api/main.py` | FastAPI with health endpoint | ✓ VERIFIED | /api/health and /ws/dashboard endpoints present |
| `hub/init-db.sql` | TimescaleDB hypertable schema | ✓ VERIFIED | sensor_readings hypertable; quality CHECK; stuck BOOLEAN |
| `hub/dashboard/server.js` | Custom Node server with WebSocket | ✓ VERIFIED (stub) | File exists and handles /ws/dashboard — but stub sends empty data only |
| `config/hub.env` | Hub configuration | ✓ VERIFIED | All required vars present; NOTE: real credential committed (CR-01) |

### Plan 01-02: MQTT Schema and Auth

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hub/mosquitto/mosquitto.conf` | allow_anonymous false + acl_file | ✓ VERIFIED | Both present; listener 1883; max_connections 50 |
| `hub/mosquitto/acl` | Per-node write restrictions | ✓ VERIFIED | hub-bridge readwrite farm/#; per-zone write-only |
| `docs/mqtt-topic-schema.md` | Topic hierarchy documented | ✓ VERIFIED | Full schema with payloads, QoS, retain flags, Phase 2 reserved topics |
| `hub/mosquitto/generate-passwords.sh` | Password generation script | ✓ VERIFIED | Executable; openssl rand -base64 16; mosquitto_passwd |

### Plan 01-03: Edge Daemon

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `edge/daemon/main.py` | Polling daemon with buffer + MQTT | ✓ VERIFIED | poll_sensors(); store-before-publish; heartbeat with retain=true |
| `edge/daemon/sensors.py` | DS18B20 + ADS1115 + Moisture drivers | ✓ VERIFIED | SensorDriver ABC; all three concrete drivers |
| `edge/daemon/buffer.py` | SQLite store-and-forward | ✓ VERIFIED | WAL mode; ORDER BY ts ASC; all methods present |
| `edge/daemon/tests/test_buffer.py` | 6 buffer tests | ✓ VERIFIED | 6 tests pass; chronological order test passes |
| `edge/systemd/farm-daemon.service` | systemd service file | ✓ VERIFIED | Restart=always; WatchdogSec=300 |

### Plan 01-04: Local Rule Engine

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `edge/daemon/rules.py` | LocalRuleEngine with 2 emergency rules | ✓ VERIFIED | IRRIGATION_SHUTOFF + COOP_HARD_CLOSE; execute_action Phase 1 stub |
| `edge/daemon/tests/test_rules.py` | 9 rule tests | ✓ VERIFIED | 9 tests pass; boundary conditions verified |

### Plan 01-05: Hub Bridge

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hub/bridge/quality.py` | Quality flag logic + stuck detection | ✓ VERIFIED | apply_quality_flag(); StuckDetector class with 30-reading threshold |
| `hub/bridge/calibration.py` | Calibration offset application | ✓ VERIFIED | CalibrationStore; apply_calibration() |
| `hub/bridge/main.py` | MQTT pipeline with DB write | ✓ VERIFIED | Full pipeline: parse→calibrate→quality→stuck→insert→notify |
| `hub/api/ws_manager.py` | WebSocket connection manager | ✓ VERIFIED (orphaned) | Correct implementation; never reached by browser WS clients |
| `hub/bridge/tests/test_quality.py` | Quality/stuck tests | ✓ VERIFIED | 18 tests pass |

### Plan 01-06: Dashboard Components

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `hub/dashboard/src/lib/types.ts` | TypeScript types | ✓ VERIFIED | ZoneState, NodeState, QualityFlag, WSMessage union all present |
| `hub/dashboard/src/lib/ws.svelte.ts` | WebSocket reactive store | ✓ VERIFIED (wired wrong) | DashboardStore connects to wrong endpoint (server.js stub via Caddy) |
| `hub/dashboard/src/lib/SensorValue.svelte` | Sensor value row with quality badge | ✓ VERIFIED | tabular-nums; quality badge with correct colors; null state |
| `hub/dashboard/src/lib/ZoneCard.svelte` | Zone card with stale/stuck | ✓ VERIFIED | $derived state; STALE border; stuck indicator; opacity dimming |
| `hub/dashboard/src/lib/NodeHealthRow.svelte` | Node health row | ✓ VERIFIED | ONLINE/OFFLINE badges; "Heartbeat Ns ago" copy |
| `hub/dashboard/src/lib/SystemHealthPanel.svelte` | System health container | ✓ VERIFIED | 180s offline threshold; "No nodes connected" empty state |
| `hub/dashboard/src/routes/+page.svelte` | Full dashboard page | ✓ VERIFIED | dashboardStore wired; aria-live; role="status"; responsive grid |
| `hub/dashboard/src/lib/SensorValue.test.ts` | SensorValue unit tests | ✗ MISSING | File not created despite being in plan files_modified |
| `hub/dashboard/src/lib/ZoneCard.test.ts` | ZoneCard unit tests | ✗ MISSING | File not created despite being in plan files_modified |
| `hub/dashboard/src/lib/NodeHealthRow.test.ts` | NodeHealthRow unit tests | ✗ MISSING | File not created despite being in plan files_modified |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `hub/docker-compose.yml` | `hub/Caddyfile` | Caddyfile:/etc/caddy/Caddyfile volume mount | ✓ WIRED | Pattern found |
| `hub/docker-compose.yml` | `hub/init-db.sql` | init-db.sql:/docker-entrypoint-initdb.d volume | ✓ WIRED | Pattern found |
| `hub/mosquitto/mosquitto.conf` | `hub/mosquitto/acl` | acl_file directive | ✓ WIRED | acl_file present |
| `hub/docker-compose.yml` | `hub/mosquitto/mosquitto.conf` | volume mount | ✓ WIRED | mosquitto.conf:/mosquitto/config/mosquitto.conf present |
| `edge/daemon/main.py` | `edge/daemon/buffer.py` | import + buffer.store() before publish | ✓ WIRED | buffer.store() called; ReadingBuffer imported |
| `edge/daemon/main.py` | `edge/daemon/sensors.py` | import + sensor.read() in poll loop | ✓ WIRED | sensor.read() called inside poll_sensors() |
| `edge/daemon/main.py` | MQTT topics | publishes to farm/{node_id}/sensors/{type} | ✓ WIRED | farm/ topics in poll_sensors() and heartbeat |
| `edge/daemon/main.py` | `edge/daemon/rules.py` | rule_engine.evaluate() after poll | ✓ WIRED | rule_engine.evaluate(latest_readings) called; execute_action() called |
| `hub/bridge/main.py` | `hub/bridge/quality.py` | apply_quality_flag() on each reading | ✓ WIRED | apply_quality_flag() called in process_sensor_message() |
| `hub/bridge/main.py` | `hub/bridge/calibration.py` | apply_calibration() before DB insert | ✓ WIRED | calibration_store.apply_calibration() called |
| `hub/bridge/main.py` | `hub/api/ws_manager.py` | HTTP POST /internal/notify → broadcast() | ✓ WIRED | notify_api() → api:8000/internal/notify → ws_manager.broadcast() |
| `hub/dashboard/src/routes/+page.svelte` | `hub/dashboard/src/lib/ws.svelte.ts` | imports dashboardStore | ✓ WIRED | dashboardStore imported and used |
| `hub/dashboard/src/lib/ZoneCard.svelte` | `hub/dashboard/src/lib/SensorValue.svelte` | renders SensorValue for each sensor | ✓ WIRED | SensorValue components used for moisture/pH/temperature |
| `hub/dashboard/src/lib/ws.svelte.ts` | `/ws/dashboard` WebSocket URL | WebSocket connection | ✗ WIRED WRONG | Connects to /ws/dashboard which Caddy routes to dashboard:3000 (server.js stub); FastAPI ws_manager at api:8000 is never reached |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `hub/dashboard/src/lib/ZoneCard.svelte` | zone (ZoneState) | dashboardStore.zones Map | No — Map populated from WS messages, but WS delivers server.js empty stub | ✗ HOLLOW — wired but data disconnected |
| `hub/dashboard/src/lib/SystemHealthPanel.svelte` | nodes (Map<string, NodeState>) | dashboardStore.nodes Map | No — Map populated from WS heartbeat messages that never arrive | ✗ HOLLOW — wired but data disconnected |
| `hub/dashboard/src/lib/ws.svelte.ts` | zones/nodes $state | WebSocket messages from /ws/dashboard | No — receives only empty {} snapshot from server.js | ✗ DISCONNECTED |
| `hub/bridge/main.py` | sensor readings | MQTT farm/+/sensors/# subscription | Yes — asyncpg INSERT to sensor_readings hypertable | ✓ FLOWING |
| `hub/api/ws_manager.py` | _zone_states/_node_states | /internal/notify POST from bridge | Yes — update_state() called on each bridge delta | ✓ FLOWING (but no clients ever connect) |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Edge buffer tests pass | `cd edge/daemon && python -m pytest tests/ -q` | 15 passed in 0.12s | ✓ PASS |
| Bridge pipeline tests pass | `cd hub/bridge && python -m pytest tests/ -q` | 25 passed in 0.07s | ✓ PASS |
| Dashboard build succeeds | `hub/dashboard/build/` directory exists | build/handler.js present | ✓ PASS |
| Dashboard vitest tests | `cd hub/dashboard && npx vitest run` | No test files found | ✗ FAIL — 3 test files missing |
| docker compose validates | `cd hub && docker compose config --quiet` | Skipped — would require Docker context | ? SKIP |
| Edge daemon imports | `python -c "from buffer import ReadingBuffer; from sensors import DS18B20Driver"` | Skipped — requires edge/daemon/ context | ? SKIP |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| INFRA-01 | 01-01 | Hub stack via Docker Compose | ✓ SATISFIED | docker-compose.yml with 6 services; all images and volumes defined |
| INFRA-02 | 01-05 | Edge MQTT publish with QoS 1; hub writes to TimescaleDB with quality flags | ✓ SATISFIED | Bridge pipeline: QoS 1 in daemon; apply_quality_flag() in bridge; asyncpg INSERT to TimescaleDB |
| INFRA-03 | 01-03 | SQLite buffer with flush on reconnect, original timestamps | ✓ SATISFIED | ReadingBuffer WAL SQLite; store-before-publish; on_connect flush; ORDER BY ts ASC |
| INFRA-04 | 01-04 | Edge local rule engine for emergency actions without hub | ✓ SATISFIED | LocalRuleEngine with IRRIGATION_SHUTOFF and COOP_HARD_CLOSE; 9 tests pass |
| INFRA-05 | 01-05 | Hub monitors heartbeats; alerts if node misses 3 consecutive | ~ PARTIAL | Heartbeats written to node_heartbeats table; dashboard shows offline at 180s — but WS routing gap means offline status never displays to user |
| INFRA-06 | 01-06 | Freshness timestamp; stale flag after 5 minutes | ~ PARTIAL | isStale() and ZoneCard stale state implemented; WS routing gap prevents data from flowing to display |
| INFRA-07 | 01-05 | Static-reading detection (30+ consecutive identical) | ~ PARTIAL | StuckDetector implemented and tested; stuck boolean stored in DB; WS routing gap prevents stuck flag from reaching dashboard |
| INFRA-08 | 01-02 | MQTT topic schema and per-node ACL defined before any node software | ✓ SATISFIED | mosquitto.conf, acl, mqtt-topic-schema.md all exist; per-node ACL enforced |
| INFRA-09 | 01-01 | Local HTTPS via Caddy | ? HUMAN | Caddyfile has tls internal; requires running hardware to verify browser trust |
| ZONE-01 | 01-03 | Zone configurable metadata in schema | ✓ SATISFIED | zone_config table in init-db.sql with all required columns |
| ZONE-02 | 01-03 | Zone nodes poll moisture/pH/temperature on configurable interval | ✓ SATISFIED | poll_sensors() with POLL_INTERVAL_SECONDS; DS18B20, ADS1115PHDriver, MoisturePlaceholder |
| ZONE-03 | 01-05 | Calibration offsets applied at ingestion | ✓ SATISFIED | CalibrationStore.apply_calibration() called before quality flag; calibration_offsets table in schema |
| ZONE-04 | 01-06 | Dashboard shows live readings with freshness/quality | ✗ BLOCKED | Dashboard components correct; WS routing gap prevents data delivery |
| IRRIG-03 | 01-04 | NC solenoid valves — procurement requirement documented | ? UNCERTAIN | ROADMAP.md has hardware procurement checklist; no separate procurement doc in docs/; requirement is "documented for hardware selection" — the ROADMAP serves this purpose |
| COOP-04 | 01-04 | Linear actuator with limit switches — procurement requirement documented | ? UNCERTAIN | Same as IRRIG-03 — documented in ROADMAP hardware checklist |
| UI-04 | 01-01, 01-06 | Dashboard accessible from LAN via HTTPS | ? HUMAN | Infrastructure in place; requires running hardware to verify |
| UI-07 | 01-06 | System health panel with node online/offline and heartbeat | ~ PARTIAL | SystemHealthPanel with 180s offline threshold implemented; WS routing gap prevents real node data from appearing |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `hub/dashboard/server.js` | 17 | WebSocket sends static empty `{zones:{}, nodes:{}}` — no data connection | 🛑 Blocker | Dashboard displays empty state forever; cannot show live sensor readings |
| `hub/Caddyfile` | 8-10 | `/ws/dashboard` routes to `dashboard:3000` instead of `api:8000` | 🛑 Blocker | Real WebSocket data (in FastAPI ws_manager) is unreachable from browser |
| `config/hub.env` | 6 | Real credential `MQTT_BRIDGE_PASS=I9VDCVWWPH5NkmEWhyc61A==` committed to git | 🛑 Blocker | Anyone with repo access can authenticate as hub-bridge with full farm/# readwrite |
| `hub/bridge/main.py` | 127-131 | `notify_api` silently swallows all exceptions with bare `except Exception: pass` | ⚠️ Warning | WS notify failures are invisible; dashboard appears healthy when no data is flowing |
| `edge/daemon/buffer.py` | 15 | Single SQLite connection shared across threads (paho background thread + main thread) | ⚠️ Warning | ProgrammingError on concurrent buffer access during MQTT reconnect flush |
| `edge/daemon/rules.py` | 71-79 | COOP_HARD_CLOSE fires every poll cycle past the close hour, not once per evening | ⚠️ Warning | Will repeatedly actuate coop door when Phase 2 GPIO is wired |
| `hub/docker-compose.yml` | 32-38 | `bridge` and `api` use `depends_on` without `condition: service_healthy` for timescaledb | ⚠️ Warning | Crash-loop on cold start until TimescaleDB is ready |
| `hub/api/main.py` | 30-34 | `/internal/notify` endpoint has no authentication | ⚠️ Warning | Any process on hub can inject arbitrary readings to all WS clients |
| `edge/daemon/main.py` | 142-146 | Sensor list hardcoded to zone sensors regardless of NODE_TYPE=coop | ⚠️ Warning | Coop nodes attempt to init zone sensors, log errors, publish to wrong topics |

---

## Human Verification Required

### 1. HTTPS Accessibility via LAN Browser

**Test:** Start hub with `cd hub && docker compose up -d`. Open `https://localhost` (or hub LAN IP) in a browser. On second visit, verify no certificate warning is shown (Caddy local CA installed).
**Expected:** Dashboard loads over HTTPS; subsequent visits after CA installation require no manual certificate acceptance.
**Why human:** Requires running hardware; cannot verify certificate trust chain programmatically.

### 2. MQTT Credential Rotation

**Test:** Check that `config/hub.env` in git has `MQTT_BRIDGE_PASS=CHANGE_ME` as a placeholder, not a real base64 value. Run `git log --oneline config/hub.env` to confirm the real credential is not in history.
**Expected:** hub.env has placeholder; file is in .gitignore; real credential only exists on the deployed hub machine.
**Why human:** Requires operator action to rotate credential, update .gitignore, and verify git history does not contain the real value.

### 3. IRRIG-03 and COOP-04 Hardware Procurement Documentation

**Test:** Confirm that hardware procurement decisions for NC solenoid valves and linear actuator with limit switches are recorded in a dedicated document (not just ROADMAP hardware checklist), signed off by the operator before actuator integration.
**Expected:** A docs/hardware-procurement.md or similar explicitly lists confirmed hardware model/spec for irrigation valves and coop door actuator.
**Why human:** The REQUIREMENTS say "procurement requirement documented for hardware selection" — this may or may not require a separate document beyond the ROADMAP checklist; operator judgment required.

---

## Gaps Summary

**Root cause:** One architectural gap causes 5 of the 6 failed truths: the WebSocket routing mismatch.

**The gap:** `hub/Caddyfile` routes `/ws/dashboard` to `dashboard:3000` (server.js), which sends an empty stub snapshot with no connection to real sensor data. The real WebSocket manager with live sensor data and node state lives in FastAPI at `api:8000/ws/dashboard`. Caddy only routes `/api/*` to `api:8000`, so the FastAPI WebSocket endpoint is never reached by browser clients.

**Fix is a single-point change:** Either change Caddyfile to route `/ws/dashboard` to `api:8000`, OR update `server.js` to proxy WebSocket connections to `api:8000`. Both approaches work; the Caddyfile change is simpler (one line change, removes server.js WS handling entirely).

**Secondary gap:** Three dashboard unit test files (`SensorValue.test.ts`, `ZoneCard.test.ts`, `NodeHealthRow.test.ts`) were listed in plan 01-06's `files_modified` but were never created. `npx vitest run` exits with code 1 (no test files found).

**Security note not blocking phase goal but requiring immediate attention:** Real MQTT credential committed to `config/hub.env` (code review CR-01). This does not block the Phase 1 software goal but is a security requirement before any deployment to actual hardware.

**All other pipeline stages are fully implemented and tested:**
- Edge daemon: 15 unit tests pass; store-and-forward buffer, sensor drivers, rule engine all wired
- Hub bridge: 25 unit tests pass; quality flags, calibration, stuck detection, heartbeat all work
- Dashboard components: fully implemented per UI-SPEC; stale/stuck/quality display logic is correct
- The WS routing fix is the only change needed to make the full pipeline functional

---

_Verified: 2026-04-08T17:11:31Z_
_Verifier: Claude (gsd-verifier)_
