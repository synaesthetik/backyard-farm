# Phase 1: Hardware Foundation and Sensor Pipeline - Research

**Researched:** 2026-04-07
**Domain:** Embedded IoT sensor pipeline — Raspberry Pi, MQTT, TimescaleDB, FastAPI, SvelteKit
**Confidence:** HIGH (core stack), MEDIUM (SvelteKit WebSocket integration), HIGH (Docker image availability)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Soil moisture sensor TBD — research spike required in plan 01-03 (capacitive I2C vs ADS1115 ADC). Moisture model selection drives I2C multiplexer (TCA9548A) need.
- **D-02:** pH sensor: Analog pH probe + ADS1115 ADC over I2C. Calibration via pH 4.0 and 7.0 buffer solutions; offsets stored per-sensor on hub, applied at ingestion.
- **D-03:** Temperature sensor: DS18B20 waterproof probe on 1-wire bus, using `w1-therm` Linux kernel module. Multiple DS18B20 sensors share one GPIO pin.
- **D-04:** Edge node hardware: Raspberry Pi Zero 2W, 64-bit Raspberry Pi OS Lite (no desktop). GPIO and 1-wire must work on Pi Zero 2W GPIO header.
- **D-05:** I2C multiplexer decision deferred to D-01 moisture research spike. If moisture and pH ADS1115 share conflicting I2C addresses, a TCA9548A multiplexer is required.
- **D-06:** Hub: Raspberry Pi 5 8GB. Docker Compose targets ARM64 (linux/arm64) base images for ALL services.
- **D-07:** Hub storage: SSD via USB3 or NVMe HAT. Docker Compose volumes for TimescaleDB data must point to SSD mount path (not SD card), e.g., `/mnt/ssd/data`.
- **D-08:** Hub static IP and NTP: Configure DHCP reservation or static IP in OS network config; install and configure `chrony` as NTP server for LAN; document assigned IP in `config/hub.env`.
- **D-09:** MQTT QoS 1 for all sensor publishes. Per-node ACL credentials defined before any node software is written (INFRA-08). Topic schema and ACL design (plan 01-02) must be completed before plan 01-03 (edge daemon).
- **D-10:** Quality flag method: range-based per sensor type. Applied at ingestion in hub MQTT bridge (plan 01-05). Stateless, no history required.
- **D-11:** Default sensor plausible ranges (configurable via env vars): Soil moisture BAD <0/>100%, SUSPECT <2/>98%, GOOD 2-98%. pH BAD <0/>14, SUSPECT <3/>10, GOOD 3-10. Temperature BAD <-10/>80°C, SUSPECT <0/>60°C, GOOD 0-60°C.
- **D-12:** Stuck-reading detection is a SEPARATE display state — does NOT downgrade the quality flag. A GOOD reading that is identical for 30+ consecutive readings is GOOD + STUCK. TimescaleDB must store a `stuck` boolean column alongside `quality`.
- **D-13:** Emergency irrigation shutoff: edge node forces relay closed at >=95% VWC. Stored as `EMERGENCY_MOISTURE_SHUTOFF_VWC` env var (default: 95).
- **D-14:** Coop door hard-close: time limit only (no hub-silence trigger in Phase 1). Force-close at or after `COOP_HARD_CLOSE_HOUR` (default: 21, meaning 21:00 local time).
- **D-15:** Dashboard: SvelteKit + Svelte 5 runes. Dark theme. Four components: ZoneCard, SensorValue, NodeHealthRow, SystemHealthPanel. NO component library — hand-authored Svelte 5 only. Lucide icons (`lucide-svelte`), Inter font (`@fontsource/inter`).
- **D-16:** Real-time updates via WebSocket to `/ws/dashboard`. Server sends full state snapshot on connect, then deltas. Stale logic runs client-side using `received_at` timestamp. Do not clear values on disconnect.

### Claude's Discretion

- SQLite schema for edge node local buffer (column names, index strategy)
- TimescaleDB hypertable schema (column names beyond required: `zone_id`, `sensor_type`, `value`, `quality`, `stuck`, `received_at`, `calibration_applied`)
- MQTT topic schema design (within the structure documented in plan 01-02)
- Reconnect backoff strategy for edge node MQTT client
- FastAPI endpoint design for WebSocket `/ws/dashboard` and any REST endpoints needed for zone config
- Python vs other language for hub MQTT bridge (Python with paho-mqtt/aiomqtt is the natural choice given FastAPI)
- Mosquitto configuration details (persistence, logging levels, listener ports)
- Caddy configuration for local HTTPS (self-signed vs mkcert vs `tls internal` local CA)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within Phase 1 scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Hub service stack runs via Docker Compose (Mosquitto, TimescaleDB, FastAPI, Caddy) — no cloud dependency | All four Docker images confirmed ARM64-available; Docker Compose v5.0.1 on dev machine |
| INFRA-02 | Edge nodes publish via MQTT QoS 1; hub subscribes and writes to TimescaleDB with quality flags (GOOD/SUSPECT/BAD) at ingestion | paho-mqtt 2.1.0 / aiomqtt 2.5.1 for edge; asyncpg 0.31.0 + TimescaleDB 2.26.1 for hub write |
| INFRA-03 | Each edge node maintains a local SQLite buffer; data flushed to hub on reconnect with original timestamps preserved | Store-and-forward pattern well-documented; sqlite3 3.43.2 available; paho-mqtt reconnect callbacks support flush-on-reconnect |
| INFRA-04 | Edge nodes run local rule engine for emergency-threshold actions without hub involvement | Pure Python, no external deps; rule engine is synchronous code in the daemon |
| INFRA-05 | Hub monitors edge node heartbeats; alerts if node misses 3 consecutive 60-second heartbeats | Heartbeat tracking in TimescaleDB or in-memory dict; WebSocket push to dashboard |
| INFRA-06 | All sensor readings displayed with freshness timestamp; readings >5 min flagged stale in UI | Client-side stale detection from `received_at` field; Svelte 5 `$derived` for computed stale state |
| INFRA-07 | Static-reading detection flags sensors returning same value for 30+ consecutive readings | Consecutive-equality counter stored per sensor in bridge service memory; `stuck` boolean written to TimescaleDB |
| INFRA-08 | MQTT topic schema and per-node ACL credentials defined before any node software is written | Mosquitto 2.x password file + ACL file pattern; `mosquitto_passwd` utility for credential generation |
| INFRA-09 | Hub serves local HTTPS via Caddy (required for PWA install on iOS) | Caddy `tls internal` or mkcert approach; Caddy Docker image confirmed ARM64 (March 2026) |
| ZONE-01 | Each garden zone has configurable metadata: plant type, soil type, target VWC range, pH target range, irrigation zone ID | FastAPI REST endpoint for zone config; config stored in TimescaleDB or simple JSON; served to dashboard on WebSocket connect |
| ZONE-02 | Zone nodes poll soil moisture (VWC %), pH, temperature on configurable interval and publish via MQTT | Sensor daemon polling loop; configurable via `POLL_INTERVAL_SECONDS` env var |
| ZONE-03 | Hub applies per-sensor calibration offsets at ingestion before writing to TimescaleDB | Calibration offsets stored in config table; applied in MQTT bridge before insert |
| ZONE-04 | Dashboard shows live sensor readings per zone with freshness timestamp and quality flag indicator | ZoneCard component per UI-SPEC; SensorValue sub-component; WebSocket delta updates |
| IRRIG-03 | All irrigation valves are normally-closed (NC) solenoids — procurement requirement documented | Hardware procurement checklist documented in ROADMAP.md; must be verified before plan 01-04 |
| COOP-04 | Coop door actuator uses linear actuator with physical limit switches — procurement requirement documented | Hardware procurement checklist documented in ROADMAP.md; must be verified before plan 01-04 |
| UI-04 | Web dashboard accessible from any browser on LAN via HTTPS | Caddy reverse proxy + HTTPS; hub IP documented in `config/hub.env`; Svelte build served via adapter-node |
| UI-07 | System health panel shows each node's online/offline status, last heartbeat timestamp, data freshness indicator | SystemHealthPanel + NodeHealthRow components per UI-SPEC; driven by heartbeat tracking in hub |

</phase_requirements>

---

## Summary

Phase 1 builds a complete IoT sensor pipeline from hardware to dashboard. The stack is deliberately standard: Mosquitto (MQTT broker), TimescaleDB (time-series storage), FastAPI (API + WebSocket), Caddy (local HTTPS reverse proxy), and SvelteKit (dashboard UI). All Docker images are confirmed ARM64-compatible and actively maintained as of April 2026.

The most complex integration point is the SvelteKit WebSocket server. SvelteKit with `adapter-node` does not natively expose a WebSocket upgrade path — the recommended production approach is a custom Node.js server that wraps the SvelteKit handler and attaches a `ws` WebSocket server on the same HTTP server instance. This is a one-time plumbing task at project setup.

The hub MQTT bridge is the quality-and-calibration enforcement point. It must be an async Python service (aiomqtt + asyncpg) that reads from Mosquitto, applies calibration offsets, evaluates quality flags, tracks consecutive-reading equality for stuck detection, and writes to TimescaleDB — all in one pipeline stage before any data reaches the dashboard.

**Primary recommendation:** Use aiomqtt (async wrapper around paho-mqtt) for the hub MQTT bridge co-located with FastAPI, and paho-mqtt 2.x directly on edge nodes (simpler, synchronous daemon). Use Caddy `tls internal` for hub HTTPS — one-time `caddy trust` install on each browser device, no recurring cert work.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| eclipse-mosquitto | 2.1.2 | MQTT broker | Official image, ARM64 confirmed, Mosquitto 2.x required for explicit auth |
| timescale/timescaledb | 2.26.1-pg17 | Time-series database (TimescaleDB on PostgreSQL 17) | ARM64 confirmed (updated 2026-04-05); pg17 is current; OSS variant available |
| FastAPI | 0.135.3 | Hub API server + WebSocket endpoint | Current release; Python native; asyncpg integration well-documented |
| uvicorn | 0.44.0 | ASGI server for FastAPI | Standard FastAPI production server |
| caddy (official) | latest (2026-03-10) | Local HTTPS reverse proxy | ARM64 confirmed; `tls internal` for LAN cert; zero config cert renewal |
| aiomqtt | 2.5.1 | Async MQTT client for hub MQTT bridge | Async wrapper over paho-mqtt; idiomatic asyncio; 2.4.0 released May 2025 |
| asyncpg | 0.31.0 | Async PostgreSQL driver for TimescaleDB writes | Fastest Python Postgres driver; used with FastAPI connection pool |
| paho-mqtt | 2.1.0 | MQTT client for edge nodes | Synchronous, zero-dependency; standard for edge daemon scripts |
| w1thermsensor | 2.3.0 | DS18B20 temperature sensor Python driver | Wraps `/sys/bus/w1` filesystem; handles multi-sensor addressing |
| adafruit-circuitpython-ads1x15 | 3.0.3 | ADS1115 16-bit ADC driver (pH sensor) | Official Adafruit driver; I2C; supports address pin config |
| SvelteKit | 2.56.1 | Dashboard frontend framework | Current release; Svelte 5 runes included |
| svelte | 5.55.1 | UI reactivity (runes) | Current release; `$state`, `$derived`, `$effect` runes |
| lucide-svelte | 1.0.1 | Icon library | MIT; tree-shakeable; locked by UI-SPEC |
| @fontsource/inter | 5.2.8 | Self-hosted Inter font | Locked by UI-SPEC; no runtime Google Fonts CDN call |
| @sveltejs/adapter-node | 5.5.4 | SvelteKit Node.js build adapter | Required for custom server + WebSocket integration |
| ws | 8.20.0 | WebSocket server library (Node.js) | Used in custom SvelteKit server to handle `/ws/dashboard` upgrades |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12.5 | Data validation in FastAPI models | All incoming MQTT payloads and API request/response schemas |
| python-dotenv | current | Load env vars from `.env` files | Hub bridge service and edge node daemon configuration |
| chrony | distro-version | NTP server on hub | Hub-as-NTP-server for LAN (edge nodes sync to hub); preferred over ntpd on Pi OS |
| vitest | 4.1.3 | Unit testing for Svelte 5 components | Svelte 5 requires vitest + @testing-library/svelte for component tests |
| pytest | 9.0.2 | Python unit testing for hub bridge, edge daemon | Standard Python test runner |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiomqtt (hub bridge) | fastapi-mqtt | fastapi-mqtt wraps gmqtt (not paho); less battle-tested; aiomqtt is more actively maintained and uses paho under the hood |
| Caddy tls internal | mkcert + custom CA | mkcert requires running `mkcert -install` on every LAN browser device; Caddy tls internal is equivalent but self-contained in the container |
| adafruit-ads1x15 | smbus2 / raw I2C | adafruit driver handles ADS1115 register layout correctly; smbus2 requires manual register-level implementation |
| w1thermsensor | direct `/sys/bus/w1` file read | w1thermsensor handles multi-sensor addressing and error recovery; direct file read is sufficient but requires more code |
| paho-mqtt on edge | aiomqtt on edge | Pi Zero 2W with 512MB RAM; synchronous paho daemon is simpler and uses less memory than asyncio loop |
| timescaledb (pg17) | plain PostgreSQL | TimescaleDB adds hypertable compression, time_bucket(), and retention policies — essential for Phase 4 training data management |

**Installation (hub services — Python):**
```bash
pip install fastapi==0.135.3 uvicorn==0.44.0 aiomqtt==2.5.1 asyncpg==0.31.0 pydantic==2.12.5 python-dotenv
```

**Installation (edge node — Python):**
```bash
pip install paho-mqtt==2.1.0 w1thermsensor==2.3.0 adafruit-circuitpython-ads1x15==3.0.3 python-dotenv
```

**Installation (dashboard — Node.js):**
```bash
npm create svelte@latest dashboard
npm install lucide-svelte @fontsource/inter ws
npm install -D @sveltejs/adapter-node vitest @testing-library/svelte
```

**Version verification:** All versions verified against npm registry and PyPI as of 2026-04-07.

---

## Architecture Patterns

### Recommended Project Structure

```
backyard-farm/
├── hub/
│   ├── docker-compose.yml          # Mosquitto, TimescaleDB, FastAPI, Caddy
│   ├── mosquitto/
│   │   ├── mosquitto.conf
│   │   ├── passwd                  # generated by mosquitto_passwd
│   │   └── acl                     # per-node topic ACLs
│   ├── bridge/                     # Hub MQTT bridge service
│   │   ├── Dockerfile
│   │   ├── main.py                 # aiomqtt subscriber + asyncpg writer
│   │   ├── quality.py              # flag logic (range checks + stuck detection)
│   │   ├── calibration.py          # offset application
│   │   └── requirements.txt
│   ├── api/                        # FastAPI service
│   │   ├── Dockerfile
│   │   ├── main.py                 # FastAPI app + WebSocket manager
│   │   ├── ws_manager.py           # WebSocket connection registry + broadcast
│   │   ├── models.py               # Pydantic models
│   │   └── requirements.txt
│   ├── dashboard/                  # SvelteKit app
│   │   ├── src/
│   │   │   ├── lib/
│   │   │   │   ├── ZoneCard.svelte
│   │   │   │   ├── SensorValue.svelte
│   │   │   │   ├── NodeHealthRow.svelte
│   │   │   │   └── SystemHealthPanel.svelte
│   │   │   └── routes/
│   │   │       └── +page.svelte    # main dashboard page
│   │   ├── server.js               # custom Node server wrapping SvelteKit + ws
│   │   └── svelte.config.js
│   └── Caddyfile
├── edge/
│   ├── daemon/
│   │   ├── main.py                 # polling loop + MQTT publish + SQLite buffer
│   │   ├── sensors.py              # DS18B20 + ADS1115 drivers
│   │   ├── buffer.py               # SQLite store-and-forward
│   │   ├── rules.py                # local rule engine (irrigation shutoff, coop hard-close)
│   │   └── requirements.txt
│   └── systemd/
│       └── farm-daemon.service
└── config/
    └── hub.env                     # hub IP, port assignments
```

### Pattern 1: MQTT Bridge with Async Pipeline

**What:** aiomqtt subscriber runs in asyncio event loop; each received message is processed synchronously (quality flag + calibration) then inserted into TimescaleDB via asyncpg connection pool. On insert, a notification is dispatched to the FastAPI WebSocket manager for push to all dashboard clients.

**When to use:** Any time a new sensor reading arrives at the broker.

**Example:**
```python
# Source: aiomqtt docs (https://github.com/empicano/aiomqtt)
async def bridge_loop(db_pool: asyncpg.Pool, ws_manager: WebSocketManager):
    async with aiomqtt.Client("localhost") as client:
        await client.subscribe("farm/+/sensors/#")
        async for message in client.messages:
            reading = parse_payload(message.payload)
            flagged = apply_quality_flag(reading)
            calibrated = apply_calibration(flagged, db_pool)
            await db_pool.execute(INSERT_SQL, *calibrated.values())
            await ws_manager.broadcast(calibrated.to_delta_json())
```

### Pattern 2: Edge Node Store-and-Forward

**What:** Edge daemon writes every reading to local SQLite before attempting MQTT publish. On successful publish, reading is marked `sent=1`. On reconnect, unsent readings are flushed in timestamp order before resuming live publishing.

**When to use:** Every sensor poll cycle, regardless of network state.

**Example:**
```python
# Store-and-forward pattern (paho-mqtt reconnect callback)
def on_connect(client, userdata, flags, rc, properties):
    # Flush buffered readings in chronological order
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, payload FROM readings WHERE sent=0 ORDER BY ts ASC"
        ).fetchall()
        for row_id, payload in rows:
            client.publish(TOPIC, payload, qos=1)
            conn.execute("UPDATE readings SET sent=1 WHERE id=?", (row_id,))
```

### Pattern 3: SvelteKit Custom Server with WebSocket

**What:** `adapter-node` build produces a `handler.js` file. A custom `server.js` creates an HTTP server, attaches both the SvelteKit handler and a `ws.WebSocketServer` for upgrade events. SvelteKit routes `/ws/dashboard` upgrade requests to the WebSocket server; all other requests go to SvelteKit.

**When to use:** Required for WebSocket support with SvelteKit adapter-node in production.

**Example:**
```javascript
// server.js — Source: https://joyofcode.xyz/using-websockets-with-sveltekit
import { createServer } from 'http'
import { WebSocketServer } from 'ws'
import { handler } from './build/handler.js'

const server = createServer(handler)
const wss = new WebSocketServer({ noServer: true })

server.on('upgrade', (req, socket, head) => {
  if (req.url === '/ws/dashboard') {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit('connection', ws, req)
    })
  }
})
```

### Pattern 4: Svelte 5 Runes for Real-Time Zone State

**What:** Dashboard maintains a `Map<zoneId, ZoneState>` as `$state`. WebSocket delta messages update individual zone entries. ZoneCard receives zone state as a prop and uses `$derived` for computed display properties (isStale, isStuck).

**When to use:** All sensor value updates from the WebSocket stream.

**Example:**
```typescript
// Source: Svelte 5 runes pattern for real-time updates
let zoneStates = $state(new Map<string, ZoneState>())

ws.onmessage = (event) => {
  const delta = JSON.parse(event.data)
  if (delta.type === 'sensor_update') {
    zoneStates.set(delta.zone_id, { ...zoneStates.get(delta.zone_id), ...delta })
    // Svelte 5 runes: Map mutation triggers reactivity
    zoneStates = new Map(zoneStates)
  }
}

// In ZoneCard.svelte
const { zone } = $props<{ zone: ZoneState }>()
const isStale = $derived(Date.now() - zone.received_at > 5 * 60 * 1000)
const isStuck = $derived(zone.stuck === true)
```

### Pattern 5: Mosquitto 2.x ACL Configuration

**What:** Mosquitto 2.x requires explicit authentication. Each edge node gets a unique username/password. ACL file grants each node write access to its own topic prefix and read access to nothing (hub bridge has a dedicated superuser credential).

**When to use:** Required before any edge node software is written (INFRA-08).

**Example:**
```
# mosquitto.conf
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwd
acl_file /mosquitto/config/acl

# acl file
user zone-01
topic write farm/zone-01/#
topic write farm/zone-01/heartbeat

user hub-bridge
topic readwrite farm/#
```

### Anti-Patterns to Avoid

- **Polling TimescaleDB for dashboard updates:** Do not have the dashboard poll a REST endpoint for sensor updates — use the WebSocket stream. Polling at 1-second intervals on a Pi 5 is unnecessary load and adds latency.
- **Writing calibration offsets to the edge node:** Calibration offsets live on the hub only and are applied at ingestion. Edge nodes send raw ADC values. This allows recalibration without touching edge node code.
- **Using `allow_anonymous true` in Mosquitto:** Mosquitto 2.x will log a warning and connection may fail. Always configure explicit auth for Phase 1 — it is required for production and QoS 1.
- **Storing raw (pre-quality-flag) data in TimescaleDB:** The bridge must apply quality flags and calibration BEFORE inserting. Phase 4 model training explicitly relies on the `quality` column to filter training data.
- **Using `display: flex` with inline `tabular-nums`:** Apply `font-variant-numeric: tabular-nums` via CSS class, not inline style, to avoid hydration mismatch in SvelteKit SSR.
- **Clearing sensor values on WebSocket disconnect:** Per D-16 and UI-SPEC, values must remain visible at last-known state. Stale logic continues client-side from `received_at` timestamp.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-series query and compression | Custom Postgres table + manual partitioning | TimescaleDB hypertable + `time_bucket()` | TimescaleDB handles chunk management, compression, and index optimization; manual time-series partitioning has many edge cases |
| MQTT reconnect with backoff | Custom reconnect loop in paho | paho-mqtt built-in `reconnect_delay_set()` + `loop_start()` | paho handles exponential backoff, thread safety, and reconnect callbacks correctly |
| ADS1115 I2C register layout | Direct smbus2 register reads | adafruit-circuitpython-ads1x15 | ADS1115 requires correct config register bit-packing and conversion factor for gain setting; Adafruit driver handles this |
| DS18B20 multi-sensor addressing | Manual `/sys/bus/w1/devices/` parsing | w1thermsensor | w1thermsensor handles device enumeration, CRC error detection, and parasitic power mode |
| Local HTTPS certificate | Self-signed cert with manual CA import | Caddy `tls internal` | Caddy manages its own local CA lifecycle, auto-renews, and `caddy trust` handles system trust store installation |
| WebSocket connection state broadcasting | Custom pub-sub registry | `ws.WebSocketServer` connection set + iteration | WebSocketServer handles binary frame encoding, ping/pong keepalive, and clean disconnect detection |

**Key insight:** The edge IoT world has many deceptively complex hardware-level abstractions (1-Wire CRC errors, I2C address conflicts, ADC gain register bits). Using proven hardware driver libraries eliminates days of debugging hardware protocol edge cases.

---

## Common Pitfalls

### Pitfall 1: TimescaleDB ARM64 Image Tag Selection

**What goes wrong:** Using `timescale/timescaledb:latest` instead of a pinned tag — `latest` on ARM64 Docker Hub may resolve to an amd64 manifest on some Docker daemon versions, causing silent emulation or pull failure.

**Why it happens:** Multi-arch manifest disambiguation can behave differently across Docker versions.

**How to avoid:** Pin to `timescale/timescaledb:2.26.1-pg17` in `docker-compose.yml` and set `platform: linux/arm64` explicitly in the service definition.

**Warning signs:** Container starts but TimescaleDB reports `FATAL: could not open file` on ARM64 hardware.

### Pitfall 2: Mosquitto 2.x Requires Explicit Auth

**What goes wrong:** Mosquitto 2.x refuses all connections when `allow_anonymous` is not set AND no auth plugin is configured — the default changed from 1.x. Edge nodes fail to connect silently (timeout, not auth error).

**Why it happens:** Breaking change in Mosquitto 2.0. The config must explicitly set `allow_anonymous false` and a `password_file`.

**How to avoid:** Always include `allow_anonymous false` and `password_file` in `mosquitto.conf`. Generate password file with `mosquitto_passwd -c /mosquitto/config/passwd <username>` before starting the container.

**Warning signs:** `Connection Refused: Not Authorized` in paho-mqtt on_connect callback with `rc=5`.

### Pitfall 3: SvelteKit WebSocket Upgrade Requires Custom Server

**What goes wrong:** `@sveltejs/adapter-node` does not expose WebSocket upgrade events by default. Connecting a WebSocket client to a standard SvelteKit adapter-node build gives a 404 or connection reset.

**Why it happens:** SvelteKit routes are built as HTTP request handlers; WebSocket is a protocol upgrade that bypasses the route system.

**How to avoid:** Use a custom `server.js` that wraps the SvelteKit `handler.js` and intercepts `server.on('upgrade', ...)` events for the `/ws/dashboard` path. This is a known pattern with `ws` library.

**Warning signs:** WebSocket connection closes immediately after handshake with status 404.

### Pitfall 4: Svelte 5 Map Reactivity

**What goes wrong:** Mutating a `Map` stored in `$state` does not trigger reactive updates in Svelte 5. Dashboard zone cards do not update when new sensor readings arrive.

**Why it happens:** Svelte 5 runes track object identity for Maps and Sets. Mutating in place (`.set()`) does not signal a change.

**How to avoid:** After mutating the Map, reassign it: `zoneStates = new Map(zoneStates)`. This creates a new reference and triggers reactivity.

**Warning signs:** WebSocket `onmessage` fires correctly but zone card values do not update in the UI.

### Pitfall 5: DS18B20 on Pi Zero 2W — 1-Wire GPIO Pin Default

**What goes wrong:** The w1-therm kernel module defaults to GPIO pin 4 (physical pin 7) on Raspberry Pi. If the DS18B20 data wire is connected to a different pin, the sensor is never detected.

**Why it happens:** `dtoverlay=w1-gpio` in `/boot/firmware/config.txt` (Pi OS Bullseye+) uses GPIO4 by default; custom pin requires `dtoverlay=w1-gpio,gpiopin=X`.

**How to avoid:** Document the chosen DS18B20 GPIO pin in hardware setup task. Use `dtoverlay=w1-gpio,gpiopin=<N>` in `/boot/firmware/config.txt` if not using GPIO4.

**Warning signs:** `/sys/bus/w1/devices/` directory is empty after boot despite sensor connected.

### Pitfall 6: ADS1115 I2C Address Conflict

**What goes wrong:** If the moisture sensor also uses ADS1115 (ADDR to GND = 0x48), it conflicts with the pH ADS1115. Both sensors on the same I2C bus with the same address results in undefined behavior.

**Why it happens:** ADS1115 has 4 possible addresses (0x48-0x4B via ADDR pin to GND/VCC/SDA/SCL). Two devices with the same address on one bus collide.

**How to avoid:** This is the D-01 research spike. If moisture uses ADS1115, the moisture sensor's ADDR pin must be configured for 0x49 (VCC), or a TCA9548A I2C multiplexer must be added. The planner must include this research spike as the first task in plan 01-03.

**Warning signs:** pH readings return garbage values or I2C bus hangs after moisture sensor is connected.

### Pitfall 7: paho-mqtt 2.x Breaking API Changes

**What goes wrong:** Code written for paho-mqtt 1.x (pre-2.0) uses deprecated callback signatures. In paho-mqtt 2.x, `on_connect` takes 5 arguments instead of 4 (added `properties`); `on_message` is unchanged but `CallbackAPIVersion.VERSION2` must be specified at client construction.

**Why it happens:** paho-mqtt 2.0 introduced `CallbackAPIVersion` to support both MQTT 3.x and 5.0 callback signatures.

**How to avoid:** Instantiate client with `mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, ...)` and use `def on_connect(client, userdata, flags, reason_code, properties)` signature.

**Warning signs:** `TypeError: on_connect() takes 4 positional arguments but 5 were given`.

### Pitfall 8: Caddy tls internal Requires One-Time Browser Trust Install

**What goes wrong:** Dashboard loads over HTTPS but browser shows certificate warning on first visit from each device.

**Why it happens:** Caddy `tls internal` generates a local CA. The CA cert must be installed in each browser's trust store on first use.

**How to avoid:** Plan 01-01 must include a task to run `caddy trust` on the hub and document the manual CA cert import procedure for each LAN device (one-time per device). After this, subsequent visits show no warning.

**Warning signs:** Browser shows "Your connection is not private" / `NET::ERR_CERT_AUTHORITY_INVALID` on initial HTTPS visit.

---

## Code Examples

### TimescaleDB Hypertable Schema

```sql
-- Source: TimescaleDB docs + IoT best practices
CREATE TABLE sensor_readings (
    time          TIMESTAMPTZ        NOT NULL,
    zone_id       TEXT               NOT NULL,
    sensor_type   TEXT               NOT NULL,   -- 'moisture' | 'ph' | 'temperature'
    value         DOUBLE PRECISION   NOT NULL,
    quality       TEXT               NOT NULL,   -- 'GOOD' | 'SUSPECT' | 'BAD'
    stuck         BOOLEAN            NOT NULL DEFAULT FALSE,
    calibration_applied BOOLEAN      NOT NULL DEFAULT FALSE,
    node_id       TEXT               NOT NULL,
    received_at   TIMESTAMPTZ        NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('sensor_readings', by_range('time', INTERVAL '1 day'));

-- Composite index for common query: readings per zone ordered by time
CREATE INDEX idx_zone_time ON sensor_readings (zone_id, time DESC);

-- Zone config table (not a hypertable — static config)
CREATE TABLE zones (
    zone_id           TEXT PRIMARY KEY,
    display_name      TEXT NOT NULL,
    plant_type        TEXT,
    soil_type         TEXT,
    target_vwc_low    DOUBLE PRECISION,
    target_vwc_high   DOUBLE PRECISION,
    target_ph_low     DOUBLE PRECISION,
    target_ph_high    DOUBLE PRECISION,
    irrigation_zone_id TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Per-sensor calibration offsets
CREATE TABLE calibration_offsets (
    sensor_id   TEXT PRIMARY KEY,   -- e.g., 'zone-01-moisture'
    zone_id     TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    offset_value DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    slope        DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    calibrated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Edge Node SQLite Buffer Schema

```sql
-- Lightweight buffer for store-and-forward on Pi Zero 2W
CREATE TABLE IF NOT EXISTS readings_buffer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,   -- ISO8601 UTC timestamp (original measurement time)
    zone_id     TEXT    NOT NULL,
    sensor_type TEXT    NOT NULL,
    raw_value   REAL    NOT NULL,
    sent        INTEGER NOT NULL DEFAULT 0,  -- 0=pending, 1=sent
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_unsent ON readings_buffer (sent, ts ASC);
```

### MQTT Topic Schema

```
farm/{zone_id}/sensors/{sensor_type}    # sensor readings
farm/{zone_id}/heartbeat                # node heartbeat (60s interval)
farm/{zone_id}/status                   # node status metadata
farm/coop/sensors/{sensor_type}         # coop node readings
farm/coop/heartbeat                     # coop node heartbeat

# Payload format (JSON, all topics)
{
  "zone_id": "zone-01",
  "sensor_type": "moisture",
  "value": 42.3,
  "ts": "2026-04-07T14:23:00Z",   # UTC ISO8601, original measurement time
  "node_id": "pi-zero-zone-01"
}
```

### Caddy tls internal Configuration

```caddyfile
# Caddyfile — Source: Caddy docs (https://caddyserver.com/docs/caddyfile/directives/tls)
{
    local_certs
}

farm.local, 192.168.1.100 {
    tls internal
    reverse_proxy /ws/* api:8000
    reverse_proxy /* dashboard:3000
}
```

### paho-mqtt 2.x Edge Daemon Skeleton

```python
# Source: paho-mqtt 2.x docs (https://eclipse.dev/paho/files/paho.mqtt.python/html/)
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        flush_buffer(client, userdata['db'])

def on_disconnect(client, userdata, flags, reason_code, properties):
    # paho handles reconnect automatically via reconnect_delay_set
    pass

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="zone-01")
client.username_pw_set("zone-01", password=os.environ['MQTT_PASSWORD'])
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.reconnect_delay_set(min_delay=1, max_delay=60)
client.connect(os.environ['MQTT_HOST'], 1883, keepalive=90)
client.loop_start()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| paho-mqtt 1.x callback API | paho-mqtt 2.x with `CallbackAPIVersion.VERSION2` | paho-mqtt 2.0 (2023) | `on_connect` signature changed; old code raises TypeError |
| ntpd on Raspberry Pi OS | chrony | Pi OS Bullseye (2021) | chrony is the default NTP daemon on modern Pi OS; ntpd no longer included |
| `/boot/config.txt` | `/boot/firmware/config.txt` | Pi OS Bookworm (2023) | Device tree overlays (w1-gpio, i2c-dev) go in the new path on Pi OS Bookworm |
| SvelteKit pages router (`__layout.svelte`) | SvelteKit file-based router (`+layout.svelte`, `+page.svelte`) | SvelteKit 1.0 (2022) | All route files use `+` prefix convention |
| Svelte 4 stores (`writable`, `readable`) | Svelte 5 runes (`$state`, `$derived`, `$effect`) | Svelte 5.0 (2024) | Runes are the primary reactivity model in Svelte 5; stores still work but are not idiomatic for new code |
| Mosquitto 1.x (anonymous by default) | Mosquitto 2.x (explicit auth required) | Mosquitto 2.0 (2021) | All Mosquitto 2.x deployments must explicitly configure authentication |

**Deprecated/outdated:**
- `asyncio-mqtt` (PyPI package): Superseded by `aiomqtt` — same maintainer renamed and rewrote the package. Do not use `asyncio-mqtt`; use `aiomqtt`.
- paho-mqtt 1.x callback signatures: Deprecated. Will be removed in a future major version. Use `CallbackAPIVersion.VERSION2` in all new code.

---

## Open Questions

1. **Moisture sensor model selection (D-01)**
   - What we know: Two candidates — capacitive I2C sensor (e.g., Stemma QT / CHIRP) vs. capacitive ADC-based (e.g., Adafruit STEMMA Soil Sensor or a raw capacitive module read via ADS1115)
   - What's unclear: Whether the chosen moisture sensor uses ADS1115 (would conflict with pH ADS1115 at 0x48) or a different I2C address; whether a TCA9548A is needed
   - Recommendation: Plan 01-03 must include a research spike task (minimum 1 day) to evaluate both options before any daemon code is written. Decision gates the entire I2C bus design.

2. **Relay board boot state (hardware test gate)**
   - What we know: Relay boards can be active-high or active-low; if active-low, GPIOs in floating state on Pi boot may trigger relays before the daemon initializes
   - What's unclear: Which relay board model will be procured; whether boot state testing will be done before plan 01-04
   - Recommendation: Plans 01-04 is gated on hardware being in hand and relay boot state test passed. Plan 01-04 should include a hardware checklist task as its first item.

3. **Hub static IP assignment**
   - What we know: D-08 specifies DHCP reservation or static IP config in the OS; IP must be documented in `config/hub.env`
   - What's unclear: Router brand/model; whether DHCP reservation is preferred over static IP in `nmconnection`
   - Recommendation: Plan 01-01 should provide both methods and let the implementer choose based on router capability. Document the chosen IP immediately after assignment.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | All hub services (01-01) | Yes | 29.1.4 | — |
| Docker Compose | Hub stack (01-01) | Yes | v5.0.1 | — |
| Node.js | SvelteKit build (01-06) | Yes | v25.3.0 | — |
| npm | SvelteKit packages (01-06) | Yes | 11.7.0 | — |
| Python 3 | Hub bridge, edge daemon | Yes | 3.10.17 | — |
| mkcert | Local CA (alternative to tls internal) | Yes | v1.4.4 | Use Caddy `tls internal` instead |
| sqlite3 CLI | Buffer schema inspection | Yes | 3.43.2 | — |
| mosquitto CLI tools | ACL testing (01-02) | Not found (dev machine) | — | Install via `brew install mosquitto` or use container `exec` |
| chrony | Hub NTP server (01-01) | Not found (dev machine) | — | Expected on Pi OS Bookworm — install via `apt install chrony` |
| pytest | Python unit tests | Yes | 9.0.2 | — |

**Target hardware notes (not dev machine — deployment targets):**
- Raspberry Pi 5 8GB (hub): ARM64; Pi OS Bookworm recommended; Docker installable via official Pi Docker install script
- Raspberry Pi Zero 2W (edge nodes): ARM64; Pi OS Lite Bookworm; no Docker required — Python daemon runs directly

**Missing dependencies with no fallback:**
- None on dev machine for the core build/test workflow.

**Missing dependencies with fallback:**
- `mosquitto` CLI on dev machine: Use `docker exec -it mosquitto mosquitto_pub/mosquitto_sub` to test ACLs from within the container.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest 9.0.2 |
| Python config | `pytest.ini` or `pyproject.toml` — none yet, Wave 0 creates |
| Python quick run | `pytest tests/ -x -q` |
| Python full suite | `pytest tests/ -v` |
| Frontend framework | vitest 4.1.3 |
| Frontend config | `vitest.config.ts` — none yet, Wave 0 creates |
| Frontend quick run | `npx vitest run` |
| Frontend full suite | `npx vitest run --coverage` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-02 | Quality flag logic (GOOD/SUSPECT/BAD range checks) | unit | `pytest tests/test_quality.py -x` | Wave 0 |
| INFRA-02 | Calibration offset application | unit | `pytest tests/test_calibration.py -x` | Wave 0 |
| INFRA-03 | SQLite buffer flush-on-reconnect ordering | unit | `pytest tests/test_buffer.py -x` | Wave 0 |
| INFRA-04 | Emergency moisture shutoff rule triggers at >=95% VWC | unit | `pytest tests/test_rules.py -x` | Wave 0 |
| INFRA-04 | Coop hard-close rule triggers at COOP_HARD_CLOSE_HOUR | unit | `pytest tests/test_rules.py -x` | Wave 0 |
| INFRA-05 | Heartbeat miss detection (3x60s) | unit | `pytest tests/test_heartbeat.py -x` | Wave 0 |
| INFRA-07 | Stuck-reading detection after 30 identical consecutive values | unit | `pytest tests/test_quality.py::test_stuck_detection -x` | Wave 0 |
| ZONE-04 / UI-07 | ZoneCard renders stale border when reading age >= 5 min | unit (vitest) | `npx vitest run src/lib/ZoneCard.test.ts` | Wave 0 |
| ZONE-04 / UI-07 | NodeHealthRow renders OFFLINE badge after 3 missed heartbeats | unit (vitest) | `npx vitest run src/lib/NodeHealthRow.test.ts` | Wave 0 |
| INFRA-09 / UI-04 | HTTPS endpoint accessible from LAN browser | smoke (manual) | Manual: open `https://farm.local` in browser | manual-only |
| D-12 | STUCK state coexists with GOOD quality flag (both visible in UI) | unit (vitest) | `npx vitest run src/lib/ZoneCard.test.ts::stuck_good_coexist` | Wave 0 |

**Manual-only justification:** HTTPS LAN accessibility test requires physical network and browser — cannot be automated in CI without a browser and LAN fixture.

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q && npx vitest run`
- **Per wave merge:** `pytest tests/ -v && npx vitest run --coverage`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `hub/bridge/tests/test_quality.py` — covers INFRA-02 quality flag logic (range checks + GOOD/SUSPECT/BAD boundaries)
- [ ] `hub/bridge/tests/test_calibration.py` — covers ZONE-03 calibration offset application
- [ ] `hub/bridge/tests/test_heartbeat.py` — covers INFRA-05 heartbeat miss detection logic
- [ ] `edge/daemon/tests/test_buffer.py` — covers INFRA-03 SQLite buffer flush ordering
- [ ] `edge/daemon/tests/test_rules.py` — covers INFRA-04 emergency shutoff and hard-close rules
- [ ] `hub/dashboard/src/lib/ZoneCard.test.ts` — covers ZONE-04, INFRA-06, INFRA-07 UI states
- [ ] `hub/dashboard/src/lib/NodeHealthRow.test.ts` — covers UI-07 node health display states
- [ ] `hub/bridge/tests/conftest.py` — shared fixtures (mock MQTT payloads, mock DB pool)
- [ ] `hub/dashboard/vitest.config.ts` — vitest + svelte plugin configuration
- [ ] Python test install: `pip install pytest pytest-asyncio` (no asyncio tests needed yet, but bridge tests will need it)

---

## Sources

### Primary (HIGH confidence)

- Docker Hub `timescale/timescaledb` API — ARM64 tag availability confirmed (2.26.1-pg17, updated 2026-04-05)
- Docker Hub `eclipse-mosquitto` API — ARM64 confirmed (2.1.2-alpine, updated 2026-02-09)
- Docker Hub `caddy` API — ARM64 confirmed (latest, updated 2026-03-10)
- PyPI `paho-mqtt` — version 2.1.0 confirmed current
- PyPI `aiomqtt` — version 2.5.1 confirmed current
- PyPI `asyncpg` — version 0.31.0 confirmed current
- PyPI `w1thermsensor` — version 2.3.0 confirmed current
- PyPI `adafruit-circuitpython-ads1x15` — version 3.0.3 confirmed current
- npm `@sveltejs/kit` — version 2.56.1 confirmed current
- npm `svelte` — version 5.55.1 confirmed current
- npm `lucide-svelte` — version 1.0.1 confirmed current
- npm `@sveltejs/adapter-node` — version 5.5.4 confirmed current
- npm `ws` — version 8.20.0 confirmed current
- [Caddy Automatic HTTPS docs](https://caddyserver.com/docs/automatic-https) — `tls internal` behavior, one-time trust store install requirement
- [Mosquitto docs](https://mosquitto.org/man/mosquitto-conf-5.html) — 2.x auth requirements, ACL file format

### Secondary (MEDIUM confidence)

- [TimescaleDB IoT guide (2026)](https://oneuptime.com/blog/post/2026-01-27-timescaledb-iot/view) — hypertable schema patterns, quality field conventions
- [joyofcode.xyz SvelteKit WebSocket guide](https://joyofcode.xyz/using-websockets-with-sveltekit) — custom server pattern with ws library (verified against `adapter-node` docs)
- [aiomqtt GitHub](https://github.com/empicano/aiomqtt) — async MQTT client pattern for asyncio+FastAPI integration
- [FlowFuse store-and-forward guide (Nov 2025)](https://flowfuse.com/blog/2025/11/store-and-forward-edge-data-buffering/) — SQLite buffer pattern for edge IoT
- [EMQ Python MQTT 2025 selection guide](https://www.emqx.com/en/blog/comparision-of-python-mqtt-client) — aiomqtt vs paho-mqtt comparison

### Tertiary (LOW confidence)

- Raspberry Pi Forum threads on DS18B20 and w1-therm module — GPIO pin defaults and `/boot/firmware/config.txt` path on Bookworm (not verified against official Pi docs directly; matches known pattern)

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — All package versions verified against live registries; all Docker images confirmed ARM64 via Docker Hub API
- Architecture: HIGH — TimescaleDB schema, MQTT bridge, and SvelteKit patterns verified against official docs and 2025/2026 sources
- Pitfalls: HIGH (Mosquitto 2.x, paho 2.x, Map reactivity) / MEDIUM (DS18B20 pin default — documented pattern, not officially verified for Pi Zero 2W specifically)
- Validation architecture: HIGH — pytest and vitest versions verified; test file locations follow project structure

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable stack; Svelte 5 and aiomqtt move faster — re-verify if more than 4 weeks pass before implementation)
