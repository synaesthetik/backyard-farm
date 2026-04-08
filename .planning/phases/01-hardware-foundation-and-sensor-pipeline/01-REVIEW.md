---
phase: "01"
phase_name: hardware-foundation-and-sensor-pipeline
status: issues
depth: standard
files_reviewed: 34
findings:
  critical: 3
  warning: 8
  info: 7
  total: 18
---

# Code Review: Phase 01 — Hardware Foundation and Sensor Pipeline

## Summary

The overall codebase is well-structured and architecturally sound: the store-and-forward buffer, MQTT pipeline, quality flagging, and WebSocket broadcast path are all implemented cleanly with good test coverage. Three critical issues require immediate attention — a real credential committed to version control, the `/internal/notify` endpoint exposed without any authentication, and a race condition in the WebSocket state snapshot. Several warnings address realistic failure scenarios that are currently silently ignored or mishandled.

---

## Critical Issues

### CR-01: Real MQTT credential committed to version control
**File:** `config/hub.env:6`
**Issue:** `MQTT_BRIDGE_PASS=I9VDCVWWPH5NkmEWhyc61A==` is a real base64-encoded credential, not a placeholder. This file is tracked by git (it appears in `git status` as modified, confirming it is version-controlled).
**Impact:** Anyone with read access to the repository can authenticate to the MQTT broker as `hub-bridge`, which has `readwrite farm/#` — full read/write access to all sensor topics and heartbeats. An attacker on the LAN can inject arbitrary sensor readings or deny service to legitimate edge nodes.
**Fix:** Rotate the credential immediately. Replace with a placeholder value (e.g. `MQTT_BRIDGE_PASS=CHANGE_ME`) in the committed file. Add `config/hub.env` to `.gitignore` and document that operators must generate credentials with `generate-passwords.sh` before first deployment.

---

### CR-02: `/internal/notify` endpoint has no authentication
**File:** `hub/api/main.py:30-34`
**Issue:** The `POST /internal/notify` endpoint accepts arbitrary `NotifyPayload` objects and broadcasts them to all connected WebSocket clients with no authentication, no origin check, and no rate limiting. Although it is intended for internal bridge→api communication only, the `api` container exposes port `127.0.0.1:8000:8000` on the host, and the Caddy proxy forwards `/api/*` to `api:8000`, so the endpoint is reachable from localhost and potentially through Caddy.
**Impact:** Any process on the hub host (or misconfigured proxy rule) can inject arbitrary `type`, `zone_id`, `sensor_type`, and `value` fields into every dashboard WebSocket client. This enables spoofed sensor readings to be displayed to operators.
**Fix:** Require a shared secret header (e.g. `X-Internal-Token`) on `/internal/notify`, verified against an env-var secret. Alternatively, bind the API on a separate internal-only port not exposed to Caddy, and have the bridge call that port directly without a Caddy route.

---

### CR-03: WebSocket snapshot sent before state is fully populated (race condition)
**File:** `hub/api/ws_manager.py:20-29`
**Issue:** In `connect()`, the snapshot (`self._zone_states`, `self._node_states`) is sent to the new client immediately after `accept()`. However, `update_state()` is only called inside `broadcast()`, which is invoked from `internal_notify`. If a client connects before any readings have arrived, it receives an empty snapshot — expected. But if a client connects *concurrently* while `broadcast()` is iterating `self.active_connections` and calling `update_state()`, the snapshot may be sent with partially-updated state. More importantly, the new client is appended to `active_connections` before the snapshot send completes; a broadcast arriving during the `await websocket.send_json(snapshot)` suspension point will attempt to send a delta to the same client before it has received its snapshot.
**Impact:** Dashboard clients may display a delta update (e.g. a sensor value change) before they have received the initial state, causing the UI to show a partial update without the baseline — specifically, zones that have not yet appeared in `this.zones` will be created from the delta alone, missing other sensor readings for that zone.
**Fix:** Append the new connection to `active_connections` only *after* the snapshot has been successfully sent. This ensures no broadcast can reach the client until after its snapshot is delivered.

---

## Warnings

### WR-01: `generate-passwords.sh` fallback silently overwrites the password file
**File:** `hub/mosquitto/generate-passwords.sh:19,25-26,31`
**Issue:** The script uses `||` to fall back from `docker compose exec` to a local `mosquitto_passwd` call. The hub-bridge entry uses `-c` (create/overwrite), but the zone and coop entries use `-b` (append). If the `docker compose exec` path succeeds for hub-bridge but fails halfway through zone creation, subsequent `||` fallbacks use `-b` against the same local file, silently mixing credentials from two different runs. Also, all generated passwords are printed to stdout with no option to suppress them — in a CI/automated context this leaks credentials to logs.
**Fix:** Separate the two flows (running vs. not running) explicitly and fail loudly if they diverge mid-run. Consider writing credentials to a temp file with restricted permissions rather than printing to stdout.

---

### WR-02: Bridge `notify_api` silently swallows all HTTP errors
**File:** `hub/bridge/main.py:123-131`
**Issue:** `notify_api` catches all exceptions with a bare `except Exception: pass`. This means database write failures that still return from `process_sensor_message` will result in the data being stored but the dashboard never being updated, with no log entry indicating the notify failed. It also masks connection errors to the API service that could indicate a broader service failure.
**Fix:** At minimum, log the exception at WARNING level: `except Exception as e: logger.warning("notify_api failed: %s", e)`. The non-critical comment is correct, but silent failure makes the system appear healthy when the dashboard is not receiving updates.

---

### WR-03: `ReadingBuffer` holds a single shared SQLite connection — not thread-safe
**File:** `edge/daemon/buffer.py:15`
**Issue:** `ReadingBuffer` creates `self._conn = sqlite3.connect(db_path)` at init time and reuses it for all operations. The edge daemon runs `client.loop_start()` which starts a background network thread, and `on_connect` calls `flush_buffer` — which calls `buffer.mark_sent()` — from that thread, while the main loop also calls `buffer.store()` and `buffer.mark_sent()`. SQLite connections are not thread-safe by default (the default `check_same_thread=True` will raise an exception on cross-thread use).
**Impact:** Under normal operation (MQTT reconnect while main loop is running), `flush_buffer` will be called from the paho network thread while `poll_sensors` may be calling `buffer.store()` from the main thread, raising `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`.
**Fix:** Either use `sqlite3.connect(db_path, check_same_thread=False)` with a threading lock protecting all buffer operations, or open a new connection per call (accepting the overhead), or move flush logic to the main loop only.

---

### WR-04: `ProcessedReading.received_at` uses deprecated `datetime.utcnow()`
**File:** `hub/bridge/models.py:36`
**Issue:** `Field(default_factory=datetime.utcnow)` uses `datetime.utcnow()`, which is deprecated since Python 3.12 and returns a naive datetime (no timezone info). The `received_at` column in TimescaleDB is `TIMESTAMPTZ`, which requires timezone-aware values for unambiguous storage.
**Impact:** `asyncpg` will accept a naive datetime and interpret it as UTC, but this reliance on implicit behavior is fragile. If the host timezone is ever changed, naive datetimes will be misinterpreted. Also, `ProcessedReading` is defined but not actually used in the bridge pipeline — `process_sensor_message` constructs the delta dict directly — so this model is dead code at present.
**Fix:** Replace `datetime.utcnow` with `lambda: datetime.now(timezone.utc)`. Also remove or wire in `ProcessedReading` to avoid the dead-code drift.

---

### WR-05: `coop` node rule fires every poll cycle once past the hard-close hour
**File:** `edge/daemon/rules.py:71-79`
**Issue:** `COOP_HARD_CLOSE` triggers whenever `current_hour >= coop_hard_close_hour`. Since `execute_action` is a stub today, this is harmless, but once GPIO control is wired in Phase 2, the coop door close action will be executed on every sensor poll (every 60 seconds) from 21:00 through midnight. If the action is not idempotent (e.g. a momentary relay trigger), this will repeatedly actuate the door.
**Fix:** Add state tracking to the rule engine to fire the hard-close action at most once per evening — e.g. a `_coop_closed_today: bool` flag that is reset when `current_hour < coop_hard_close_hour` (i.e. at the next morning poll). Add a comment noting this requirement for Phase 2 integration.

---

### WR-06: Bridge and API `depends_on` do not wait for service readiness
**File:** `hub/docker-compose.yml:32-38, 40-46`
**Issue:** `bridge` depends on `mosquitto` and `timescaledb`, and `api` depends on `timescaledb`, but neither uses `condition: service_healthy`. Only `timescaledb` has a `healthcheck` defined. On a cold start, `bridge` will attempt to connect to TimescaleDB before `pg_isready` passes, causing `asyncpg.create_pool` to fail and the bridge to crash-loop until TimescaleDB is ready.
**Fix:** Add `condition: service_healthy` to the `timescaledb` dependency for both `bridge` and `api`:
```yaml
depends_on:
  timescaledb:
    condition: service_healthy
```

---

### WR-07: `main.py` sensors list is hardcoded to zone sensors regardless of `NODE_TYPE`
**File:** `edge/daemon/main.py:142-146`
**Issue:** `main()` always initializes `[DS18B20Driver(), ADS1115PHDriver(), MoisturePlaceholder()]` regardless of `NODE_TYPE`. A coop node should use different sensors (`feed_weight`, `water_level`) but will attempt to initialize zone sensors on startup, producing repeated init errors and publishing `None` readings for moisture/ph/temperature topics that are not in the coop's ACL (which will be rejected by Mosquitto).
**Fix:** Branch sensor initialization on `NODE_TYPE`:
```python
if NODE_TYPE == "zone":
    sensors = [DS18B20Driver(), ADS1115PHDriver(), MoisturePlaceholder()]
elif NODE_TYPE == "coop":
    sensors = []  # coop sensor drivers TBD
```

---

### WR-08: Mosquitto port 1883 exposed to all interfaces
**File:** `hub/docker-compose.yml:5-6`
**Issue:** Mosquitto publishes `1883:1883` without a bind address, making it accessible on all host interfaces (e.g. `0.0.0.0:1883`). While ACL and password authentication are enforced, exposing the MQTT broker directly on the network interface is an unnecessary attack surface.
**Fix:** Bind to the LAN interface only, e.g. `192.168.1.100:1883:1883`, or use `127.0.0.1:1883:1883` if edge nodes connect via VPN/tunnel. Alternatively, document this as an intentional LAN-accessible service.

---

## Info

### IN-01: `conftest.py` imports unused `tempfile` and `os`
**File:** `edge/daemon/tests/conftest.py:2-3`
**Note:** `import tempfile` and `import os` are unused — the `tmp_path` fixture is provided by pytest natively. Remove both imports.

---

### IN-02: `python-dotenv` version unpinned in both requirements files
**File:** `edge/daemon/requirements.txt:4`, `hub/api/requirements.txt:5`, `hub/bridge/requirements.txt:4`
**Note:** `python-dotenv` is listed without a version pin in all three requirements files. All other dependencies are pinned. Add a version pin (e.g. `python-dotenv==1.0.1`) to ensure reproducible builds.

---

### IN-03: `caddy:latest` image tag not pinned
**File:** `hub/docker-compose.yml:59`
**Note:** All other images use explicit version tags, but `caddy:latest` is unpinned. A Caddy update could introduce breaking Caddyfile syntax changes or behavior differences. Pin to a specific version (e.g. `caddy:2.10.0-alpine`).

---

### IN-04: `dashboard/server.js` WebSocket server is unused stub
**File:** `hub/dashboard/server.js`
**Note:** This server creates a `WebSocketServer` that only sends an empty `{zones: {}, nodes: {}}` snapshot — it does not proxy to the FastAPI `/ws/dashboard` endpoint or integrate with real data. The actual WebSocket connection in `ws.svelte.ts` connects to `/ws/dashboard` on the same host, which Caddy proxies to `dashboard:3000`. If `server.js` is the Node.js entry point for the SvelteKit build, this disconnect means the dashboard WebSocket never receives real data through this path. Clarify whether SvelteKit is configured to use this custom server or whether WebSocket traffic is proxied directly to `api:8000`.

---

### IN-05: `test_heartbeat_delta_format` is a static dict assertion, not a real test
**File:** `hub/bridge/tests/test_heartbeat.py:24-33`
**Note:** `test_heartbeat_delta_format` constructs a literal dict and asserts its own keys exist. It does not call any production code. This test provides no coverage. It should be replaced with a test that calls `process_heartbeat_message` with a mock DB pool and verifies the returned delta.

---

### IN-06: Stuck detector uses floating-point equality comparison
**File:** `hub/bridge/quality.py:72`
**Note:** `prev[0] == value` compares floats for exact equality. For sensors with hardware noise at the last decimal place (e.g. temperature varying ±0.05°C), a truly stuck sensor may not be detected because consecutive readings differ in the final bit. Consider using an epsilon comparison (e.g. `abs(prev[0] - value) < 0.01`) for analog sensors. This is a design trade-off, not a defect, but worth documenting.

---

### IN-07: `SensorPayload` and `HeartbeatPayload` accept any `zone_id`/`node_id` string without validation against known nodes
**File:** `hub/bridge/models.py:13-24`
**Note:** Pydantic models accept any non-empty string for `zone_id`, `sensor_type`, and `node_id`. A rogue or misconfigured edge node could inject readings for arbitrary zone IDs (e.g. `zone-99`, SQL injection attempts in the zone_id field). Since `asyncpg` uses parameterized queries, SQL injection is not a risk, but phantom zone IDs will appear in the dashboard and pollute the database. Consider adding a Pydantic validator constraining `zone_id` and `sensor_type` to known enum values, or logging a warning when an unrecognized node publishes.

---

## Files Reviewed

- `config/hub.env`
- `docs/mqtt-topic-schema.md`
- `edge/daemon/.env.example`
- `edge/daemon/buffer.py`
- `edge/daemon/main.py`
- `edge/daemon/requirements.txt`
- `edge/daemon/rules.py`
- `edge/daemon/sensors.py`
- `edge/daemon/tests/conftest.py`
- `edge/daemon/tests/test_buffer.py`
- `edge/daemon/tests/test_rules.py`
- `edge/systemd/farm-daemon.service`
- `hub/api/main.py`
- `hub/api/models.py`
- `hub/api/requirements.txt`
- `hub/api/ws_manager.py`
- `hub/bridge/calibration.py`
- `hub/bridge/main.py`
- `hub/bridge/models.py`
- `hub/bridge/quality.py`
- `hub/bridge/requirements.txt`
- `hub/bridge/tests/conftest.py`
- `hub/bridge/tests/test_calibration.py`
- `hub/bridge/tests/test_heartbeat.py`
- `hub/bridge/tests/test_quality.py`
- `hub/Caddyfile`
- `hub/dashboard/server.js`
- `hub/dashboard/src/lib/NodeHealthRow.svelte`
- `hub/dashboard/src/lib/SensorValue.svelte`
- `hub/dashboard/src/lib/SystemHealthPanel.svelte`
- `hub/dashboard/src/lib/types.ts`
- `hub/dashboard/src/lib/ws.svelte.ts`
- `hub/dashboard/src/lib/ZoneCard.svelte`
- `hub/dashboard/src/routes/+page.svelte`
- `hub/docker-compose.yml`
- `hub/init-db.sql`
- `hub/mosquitto/acl`
- `hub/mosquitto/generate-passwords.sh`
- `hub/mosquitto/mosquitto.conf`
