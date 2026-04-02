# Architecture Patterns

**Domain:** Distributed edge IoT — backyard farm management
**Researched:** 2026-04-01
**Confidence:** HIGH for protocol choices and topology; MEDIUM for AI orchestration patterns (established but evolving)

---

## Recommended Architecture

### Topology: Hierarchical Hub-and-Spoke (Not Mesh, Not Flat)

**Decision:** Hub-and-spoke with autonomous fallback at each edge node.

A full mesh (every node talks to every other) is rejected because it adds O(n^2) communication complexity with no benefit — nodes don't need to coordinate with each other, only with the hub. A flat architecture (all nodes treated as equals) is rejected because the hub has meaningfully different responsibilities (aggregation, AI orchestration, dashboard serving, time-series storage) that warrant a distinct tier.

The chosen pattern is **two-tier hierarchical**: edge nodes form the leaf tier, the central hub forms the aggregation/intelligence tier. Each edge node is independently operable when the hub is unreachable.

```
                        +-----------------------+
                        |      CENTRAL HUB      |
                        |  (Raspberry Pi 5)     |
                        |                       |
                        |  [MQTT Broker]        |
                        |  [TimescaleDB]        |
                        |  [AI Orchestrator]    |
                        |  [Web Dashboard]      |
                        |  [API Server]         |
                        +-----------+-----------+
                                    |
                    Local WiFi / Ethernet (LAN)
                                    |
          +------------+-----------+-----------+------------+
          |            |                       |            |
  +-------+-----+ +----+--------+     +--------+----+ +-----+------+
  |  ZONE NODE  | |  ZONE NODE  |     |  ZONE NODE  | | COOP NODE  |
  | (Pi Zero 2W)| | (Pi Zero 2W)|     | (Pi Zero 2W)| | (Pi Zero 2W|
  |             | |             |     |             | |  or ESP32) |
  | [MQTT Pub]  | | [MQTT Pub]  |     | [MQTT Pub]  | | [MQTT Pub] |
  | [Local DB]  | | [Local DB]  |     | [Local DB]  | | [Local DB] |
  | [Actuators] | | [Actuators] |     | [Actuators] | | [Actuators]|
  | [Sensors]   | | [Sensors]   |     | [Sensors]   | | [Door/Feed]|
  +-------------+ +-------------+     +-------------+ +------------+
        |                |                   |               |
   Soil moisture    Soil moisture       Soil moisture    Door sensor
   pH sensor        pH sensor           pH sensor        Feed weight
   Temp sensor      Temp sensor         Temp sensor      Water level
   Irrigation valve Irrigation valve    Irrigation valve  Coop door motor
```

---

## Protocol Decision: MQTT as Primary Transport

**Chosen:** MQTT 5.0 with Mosquitto broker on hub.

**Rejected alternatives:**

| Protocol | Why Rejected |
|----------|-------------|
| gRPC | Request/response model does not match sensor telemetry publishing pattern; adds protobuf compilation step; poor fit for constrained hardware (ESP32 has no gRPC library) |
| REST/HTTP | Polling model inverts the natural flow (push from sensor); stateless — hub must poll every node, adding latency and resource waste; no native QoS |
| WebSockets | Better than REST but requires persistent connection management; no native message durability; MQTT is purpose-built for exactly this use case |
| AMQP | More complex than needed; heavier for constrained nodes; broker overhead higher than Mosquitto |

**Why MQTT wins:**

1. **Publish/subscribe decouples nodes from hub.** Nodes publish sensor data without needing hub to be online. With QoS 1 or 2, the broker stores messages for clients that were offline.
2. **QoS levels match the use case exactly.** Sensor telemetry → QoS 0 (fire-and-forget, acceptable loss). Actuator commands → QoS 1 (at-least-once delivery). Critical alerts (coop door failure) → QoS 2 (exactly-once).
3. **Retained messages.** Hub can publish actuator state as retained messages so newly-connected or reconnecting nodes receive current state immediately.
4. **Last Will and Testament (LWT).** Each node registers a will message on connect — if the node drops, the hub knows within seconds via the LWT topic `farm/nodes/{node_id}/status` → `offline`.
5. **Mosquitto runs on Raspberry Pi with ~3 MB RAM.** Extremely lightweight for the hub.
6. **Persistent sessions.** Nodes subscribe with a persistent session — the broker queues messages while the node is offline and delivers on reconnect (bounded queue size configurable).

**MQTT Topic Schema:**

```
# Telemetry (node → hub)
farm/zones/{zone_id}/sensors/{sensor_type}          # e.g. farm/zones/zone-1/sensors/soil_moisture
farm/zones/{zone_id}/sensors/{sensor_type}/status   # sensor health
farm/coop/sensors/{sensor_type}                     # e.g. farm/coop/sensors/feed_weight
farm/nodes/{node_id}/status                         # online/offline (LWT target)
farm/nodes/{node_id}/heartbeat                      # periodic liveness signal

# Commands (hub → node)
farm/zones/{zone_id}/actuators/{actuator}/command   # e.g. farm/zones/zone-1/actuators/valve/command
farm/coop/actuators/{actuator}/command              # e.g. farm/coop/actuators/door/command
farm/nodes/{node_id}/config                         # push config updates to node
farm/nodes/{node_id}/ota                            # OTA trigger

# Acknowledgments (node → hub)
farm/zones/{zone_id}/actuators/{actuator}/ack       # command execution result
farm/coop/actuators/{actuator}/ack                  # command execution result

# AI / recommendations (hub internal → UI via WebSocket)
farm/recommendations/{zone_or_area}                 # surfaced to dashboard
```

**Message Format:** JSON (not MessagePack or Protobuf). Rationale: human-readable, easy to debug with `mosquitto_sub`, no schema compilation step, negligible overhead at this sensor frequency (1–60s intervals). If bandwidth becomes a concern on WiFi, revisit MessagePack.

**Example sensor message:**
```json
{
  "node_id": "zone-1",
  "sensor": "soil_moisture",
  "value": 42.7,
  "unit": "percent",
  "timestamp": "2026-04-01T08:32:01Z",
  "quality": "good"
}
```

---

## Node Offline Resilience

**Requirement:** Edge nodes must continue operating autonomously when the hub is unreachable.

### Node-Side Architecture

Each edge node runs a small local process (Python or Rust) with three responsibilities:

1. **Sensor polling loop** — reads sensors on a configurable interval, stores readings in local SQLite (not just in-memory) regardless of hub connectivity.
2. **MQTT client with reconnect** — publishes to hub broker; if broker is unreachable, buffers messages in SQLite with a bounded queue (e.g. 24 hours of readings). On reconnect, flushes buffered messages in order.
3. **Local rule engine** — a minimal, human-readable rule file (YAML or TOML) defining threshold-based actuator triggers. These rules execute locally without hub involvement.

```
# /etc/farm-node/rules.yaml  (deployed to zone node)
rules:
  - name: emergency_irrigation
    condition:
      sensor: soil_moisture
      operator: less_than
      value: 15
      duration_minutes: 30     # must be below threshold for this long
    action:
      actuator: valve
      command: open
      duration_seconds: 300
    cooldown_minutes: 120        # prevent repeated triggering
    requires_approval: false     # emergency — execute without hub

  - name: irrigation_schedule
    condition:
      type: schedule
      cron: "0 6 * * *"         # 6 AM daily
    action:
      actuator: valve
      command: open
      duration_seconds: 600
    requires_approval: true      # normal — defer to hub approval
```

`requires_approval: true` rules are queued for hub delivery and do not execute locally — they only execute if the hub confirms. `requires_approval: false` rules (emergencies) run immediately.

### Hub-Side Awareness

The hub tracks node liveness via LWT and heartbeat topics. If a node goes offline:
- Dashboard shows node as "offline / autonomous mode"
- Pending approval requests for that node are held, not expired
- On reconnect, hub receives buffered sensor history, reconciles timeline in TimescaleDB

### Reconnect Behavior

```
Node reconnects → sends buffered messages with original timestamps
Hub receives → inserts into TimescaleDB with original timestamps (not arrival time)
Hub reconciles → detects gaps in time-series, marks as "buffered data" in metadata
Dashboard → shows grey "offline window" band on charts for the gap period
```

---

## Data Flow Design

### Sensor Ingestion Pipeline

```
Sensor Hardware
      |
      v
Node Sensor Driver (Python/Rust, hardware-agnostic adapter)
      |  (local polling loop, 1s - 60s configurable per sensor)
      v
Node Local SQLite (raw readings + buffer queue)
      |
      v (MQTT publish QoS 1)
Mosquitto Broker (on hub)
      |
      v
Hub MQTT Subscriber (bridge process)
      |  (validates, enriches with zone metadata)
      v
TimescaleDB (on hub)
      |
      +---> Continuous Aggregates (per-hour, per-day rollups)
      |
      +---> Real-time query layer (API server reads for dashboard)
      |
      +---> AI Feature Store (recent readings window for inference)
```

### TimescaleDB Schema

TimescaleDB is chosen over InfluxDB, Prometheus, or plain Postgres:
- Postgres-compatible (full SQL, familiar tooling)
- Hypertables handle time-series partitioning automatically
- Continuous aggregates replace manual rollup jobs
- Runs well on Raspberry Pi (fewer resources than InfluxDB cluster)
- Not cloud-dependent (unlike Prometheus which is pull-based and less suited to push IoT)

```sql
-- Main hypertable
CREATE TABLE sensor_readings (
    time        TIMESTAMPTZ NOT NULL,
    node_id     TEXT        NOT NULL,
    zone_id     TEXT,                    -- NULL for coop
    sensor_type TEXT        NOT NULL,    -- soil_moisture, ph, temp, feed_weight, etc.
    value       DOUBLE PRECISION NOT NULL,
    unit        TEXT        NOT NULL,
    quality     TEXT        NOT NULL DEFAULT 'good',  -- good, degraded, stale
    source      TEXT        NOT NULL DEFAULT 'live'   -- live, buffered, interpolated
);

SELECT create_hypertable('sensor_readings', 'time');
CREATE INDEX ON sensor_readings (node_id, sensor_type, time DESC);

-- Continuous aggregates for dashboard charts
CREATE MATERIALIZED VIEW sensor_readings_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    node_id,
    zone_id,
    sensor_type,
    AVG(value)  AS avg_value,
    MIN(value)  AS min_value,
    MAX(value)  AS max_value,
    COUNT(*)    AS sample_count
FROM sensor_readings
GROUP BY bucket, node_id, zone_id, sensor_type;

-- Events / actuator history
CREATE TABLE actuator_events (
    time          TIMESTAMPTZ NOT NULL,
    node_id       TEXT        NOT NULL,
    zone_id       TEXT,
    actuator      TEXT        NOT NULL,
    command       TEXT        NOT NULL,   -- open, close, on, off
    triggered_by  TEXT        NOT NULL,   -- local_rule, hub_approval, manual
    rule_name     TEXT,
    duration_ms   INTEGER,
    ack_received  BOOLEAN     NOT NULL DEFAULT FALSE,
    ack_time      TIMESTAMPTZ
);

SELECT create_hypertable('actuator_events', 'time');

-- Recommendations
CREATE TABLE recommendations (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    zone_id       TEXT,
    area          TEXT        NOT NULL,   -- zone-1, coop, etc.
    type          TEXT        NOT NULL,   -- irrigation, health_check, feeding, etc.
    priority      TEXT        NOT NULL,   -- urgent, high, normal, low
    title         TEXT        NOT NULL,
    description   TEXT        NOT NULL,
    suggested_action JSONB    NOT NULL,
    supporting_data  JSONB,              -- sensor readings that triggered this
    model_id      TEXT        NOT NULL,  -- which model generated it
    status        TEXT        NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, executed, expired
    reviewed_at   TIMESTAMPTZ,
    reviewed_by   TEXT,
    executed_at   TIMESTAMPTZ,
    outcome       TEXT                   -- success, failure, no_change
);
```

---

## Local AI Orchestration

### Architecture Pattern: Centralized Inference, Distributed Feature Collection

AI inference runs on the hub (Raspberry Pi 5 with 8GB RAM), not on individual edge nodes. Edge nodes are too constrained for model inference — they collect features and ship them to the hub.

```
Edge Nodes
    | (sensor readings via MQTT)
    v
Feature Aggregation Service (hub)
    | (assembles feature windows: last N readings per sensor per zone)
    v
Inference Queue (in-process, no external queue needed at this scale)
    |
    +---> Zone Health Model (ONNX or llama.cpp-based)
    |         | (soil moisture trend + pH + temp → plant health score)
    |         v
    |     Recommendation Generator
    |
    +---> Irrigation Schedule Model
    |         | (moisture trend + forecast + historical patterns → schedule suggestion)
    |         v
    |     Recommendation Generator
    |
    +---> Flock Health Model
              | (feed consumption + water + production + behavioral signals → health score)
              v
          Recommendation Generator
                  |
                  v
          Recommendation Store (PostgreSQL/TimescaleDB)
                  |
                  v (WebSocket push)
          Dashboard (pending approval display)
                  |
                  v (farmer approves)
          Command Router
                  |
                  v (MQTT publish QoS 1)
          Edge Node Actuator
```

### Model Selection Guidance

Two model tiers are appropriate for this system:

**Tier 1 — Threshold/rule models (no GPU needed, runs on Pi Zero nodes):**
- Sensor threshold rules for emergency triggers
- Schedule-based triggers (cron)
- Simple anomaly detection (value outside N standard deviations of rolling window)
- Implemented as: Python with numpy, or Rust with no ML library

**Tier 2 — Learned models (runs on hub Pi 5):**
- Irrigation optimization (time-series regression on soil moisture + crop type)
- Plant health scoring (multi-variate anomaly detection)
- Flock behavioral anomaly detection
- Implemented as: ONNX Runtime (most portable, no cloud dependency, runs on ARM64) or TFLite (good Pi support)

**Avoid on this hardware:**
- Ollama / full LLMs for sensor inference — LLMs are wrong tool for structured sensor data; use regression/classification models
- PyTorch full runtime (too heavy for Pi 5 background process alongside dashboard)
- Cloud inference APIs (violates local-only constraint)

**Model update path:** Models are ONNX files stored on hub filesystem at `/opt/farm/models/`. The AI service watches this directory — a new file triggers hot reload without service restart. Training (if any) happens offline on a development machine; only inference runs on-device.

### Inference Trigger Pattern

```python
# Conceptual trigger logic — not production code
INFERENCE_SCHEDULE = {
    "zone_health":      "every 15 minutes",
    "irrigation":       "every 1 hour",
    "flock_health":     "every 30 minutes",
}

# Additionally, event-triggered inference:
# - Any sensor reading that crosses a threshold → immediate inference for that zone
# - Any actuator acknowledgment → update model inputs, re-infer
```

### Recommendation Deduplication

The AI service must not flood the dashboard with duplicate recommendations. A recommendation is suppressed if:
- Same type + same zone has an unresolved pending recommendation
- A recommendation was rejected within the last 24 hours (back-off window, configurable per recommendation type)
- The triggering conditions have not materially changed since last recommendation (delta threshold)

---

## OTA Update Patterns

### Hub Updates

Hub runs standard OS package management (apt, Docker if containerized). Updates are manual or cron-triggered. No special OTA mechanism needed — it's a standard Linux box on your LAN.

### Edge Node Updates (Pi Zero 2W)

**Chosen pattern: Hub-served update packages + node pull on MQTT trigger.**

```
Developer machine
    | (scp or rsync)
    v
Hub update staging area (/opt/farm/updates/{node_type}/{version}/)
    |
    v
Admin publishes to MQTT topic: farm/nodes/{node_id}/ota
    with payload: { "version": "1.2.3", "url": "http://hub.local/updates/node-v1.2.3.tar.gz", "sha256": "..." }
    |
    v
Node receives OTA message
    | (downloads from hub's local HTTP server — no internet needed)
    | (verifies SHA256 before applying)
    v
Node applies update (systemd service restart or full image swap)
    | (sends ack: farm/nodes/{node_id}/ota/ack with status)
    v
Hub records update outcome in DB
```

**For ESP32 nodes:** Use ESP-IDF OTA partition scheme. Hub serves binary via HTTP on local network. Node triggers OTA via MQTT message, downloads from hub's local HTTP endpoint, verifies, boots into new partition.

**Safety guardrail:** Staged rollout — update one node, wait for healthy heartbeats for 30 minutes, then proceed to next. Rollback: publish `farm/nodes/{node_id}/ota` with previous version. Node keeps previous version in a rollback slot.

---

## Security Model (Local-Only)

**Threat model:** LAN-only system — the primary threats are accidental (misconfigured client, rogue device on home network) not adversarial. No internet exposure means no external attack surface. Design accordingly — don't over-engineer, but don't leave everything open.

### Dashboard Authentication

**Chosen:** Single shared passphrase with JWT session tokens. Not OAuth, not LDAP — one farmer, one device type.

- Dashboard login: username + password (bcrypt hashed, stored in hub's local config)
- On success: hub issues JWT with 7-day expiry (configurable)
- JWT verified on every API request and WebSocket upgrade
- Refresh token mechanism for PWA persistence
- HTTPS via self-signed cert or mkcert (local CA). Browser will show cert warning once; add exception.

**Why not mutual TLS for everything:** Adds significant cert management burden (renewing node certs, distributing CA to clients) with marginal benefit on a trusted LAN. Reserve mTLS for hub↔node if threat model escalates.

### MQTT Authentication

**Chosen:** Mosquitto password file + ACL rules. Passwords per node identity.

```
# mosquitto.conf
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl

# mosquitto acl (example)
user hub-orchestrator
topic readwrite farm/#

user zone-1-node
topic write farm/zones/zone-1/sensors/#
topic write farm/nodes/zone-1/#
topic read  farm/zones/zone-1/actuators/#
topic read  farm/nodes/zone-1/config
topic read  farm/nodes/zone-1/ota

user coop-node
topic write farm/coop/sensors/#
topic write farm/nodes/coop/#
topic read  farm/coop/actuators/#
topic read  farm/nodes/coop/config
topic read  farm/nodes/coop/ota
```

This prevents a misconfigured or compromised node from publishing to another zone's actuator topics. Nodes only write to their own sensor topics and read from their own command topics.

### Network Segmentation (Optional but Recommended)

Put hub and nodes on a dedicated IoT VLAN isolated from the main home network. Main network → IoT VLAN: blocked. IoT VLAN → main network: blocked except dashboard port (e.g. 443). Farm user accesses dashboard via browser from main network through firewall rule on that one port only.

This is a router configuration concern, not an application concern — but worth noting as a deployment recommendation.

---

## Component Boundaries

| Component | Location | Responsibility | Communicates With |
|-----------|----------|---------------|-------------------|
| Sensor Driver | Edge node | Read hardware sensors, normalize values | Local SQLite |
| Rule Engine | Edge node | Evaluate local threshold rules, trigger actuators autonomously | Sensor Driver, Actuator Driver |
| Actuator Driver | Edge node | Send commands to hardware (valves, door, etc.) | Rule Engine, MQTT subscriber |
| MQTT Client | Edge node | Publish sensor data, subscribe to commands, buffer when offline | Mosquitto broker (hub) |
| Local SQLite | Edge node | Buffer sensor readings during hub outage | MQTT Client, Rule Engine |
| Mosquitto Broker | Hub | Route MQTT messages between nodes and hub services | All nodes, Hub MQTT subscriber |
| MQTT Bridge | Hub | Subscribe to all farm topics, validate, write to TimescaleDB | Mosquitto, TimescaleDB |
| TimescaleDB | Hub | Time-series storage, continuous aggregates | MQTT Bridge, API Server, AI Orchestrator |
| AI Orchestrator | Hub | Schedule inference, generate recommendations, route commands | TimescaleDB, Recommendation Store, MQTT |
| API Server | Hub | REST + WebSocket endpoints for dashboard | TimescaleDB, Recommendation Store, Auth |
| Web Dashboard | Hub (served) | UI for monitoring, approvals, configuration | API Server (REST + WebSocket) |
| Auth Service | Hub | JWT issuance and verification | API Server |

---

## Scalability Considerations

This is a small backyard system — the primary scale concern is resilience, not throughput.

| Concern | At Current Scale (4-6 nodes) | If Expanding (10-20 nodes) | Notes |
|---------|------------------------------|---------------------------|-------|
| MQTT message volume | ~100 msg/min, trivial for Mosquitto | ~400 msg/min, still trivial | Mosquitto handles 10K+ msg/s |
| TimescaleDB storage | ~500 MB/year at 30s intervals | ~2 GB/year | Retention policies: keep raw for 90 days, keep hourly rollups for 2 years |
| Hub CPU (inference) | Idle most of time, spikes at inference triggers | Still fine on Pi 5 | ONNX inference for regression models is milliseconds |
| Hub RAM | ~2 GB for all services | ~3 GB | Pi 5 with 8 GB is fine |
| Node reconnect storms | Not a risk at this scale | 20 nodes reconnecting simultaneously — add jitter to reconnect backoff | 1–30s random backoff on reconnect |

---

## Key Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Topology | Hub-and-spoke with autonomous fallback | Nodes coordinate through hub; no peer-to-peer needed; hub down = nodes continue locally |
| Primary transport | MQTT 5.0 + Mosquitto | Purpose-built for IoT pub/sub; QoS levels match use case; LWT for node health; minimal resource use |
| Message format | JSON | Debuggable, no schema compilation, negligible overhead at this sensor frequency |
| Time-series DB | TimescaleDB | Postgres-compatible, SQL, continuous aggregates, runs on Pi, no cloud dependency |
| Node offline behavior | Local SQLite buffer + local rule engine | 24h buffer queue; emergency rules execute locally; normal rules pend hub approval |
| AI inference location | Hub only (not edge nodes) | Pi Zero too constrained for model inference; ONNX on Pi 5 is appropriate |
| AI model format | ONNX Runtime | Portable, ARM64 support, no cloud dependency, hot-reload via filesystem watch |
| OTA | Hub-served HTTP + MQTT trigger | No external package registry; hub is the local update server; SHA256 verification |
| Auth | JWT + Mosquitto ACL | Right-sized for single-user local system; not over-engineered |
| Dashboard transport | REST + WebSocket (same server) | REST for CRUD + history; WebSocket for live sensor feed and recommendation push |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Hub as Single Point of Failure for Safety Functions

**What goes wrong:** Node firmware relies on hub confirmation for emergency actions (e.g. "open coop door at dusk" requires hub response). Hub reboots at dusk → chickens locked out in rain.

**Instead:** All time-sensitive and safety-critical actions run from local rule engine on the node. Hub involvement is for optimization and non-emergency recommendations only. The local rules are the safety net.

### Anti-Pattern 2: Polling from Hub Instead of Push from Nodes

**What goes wrong:** Hub polls each node via HTTP every N seconds for sensor readings. Hub goes offline → sensor history gaps. Hub restarts → must re-poll all nodes to catch up. Polling interval limits real-time responsiveness.

**Instead:** Nodes push via MQTT. Hub subscribes. No polling. Nodes buffer locally when hub is unreachable and flush on reconnect.

### Anti-Pattern 3: In-Memory Buffers for Node Offline Queue

**What goes wrong:** Node loses power during hub outage. In-memory buffer lost. 12 hours of sensor data gone.

**Instead:** SQLite on node's SD card. Durability survives power loss. Bounded size (e.g. 24h rolling window) prevents filling the card.

### Anti-Pattern 4: Running LLMs for Sensor Inference

**What goes wrong:** Ollama running on hub Pi 5 consumes 4-6 GB RAM, competes with dashboard and TimescaleDB, produces verbose outputs that must be re-parsed into structured commands, adds latency of seconds per inference.

**Instead:** ONNX regression/classification models for sensor data. LLMs are appropriate for natural language interfaces (future feature) not for "is this soil moisture reading anomalous."

### Anti-Pattern 5: Skipping Message Acknowledgments for Actuator Commands

**What goes wrong:** Hub publishes "open valve" command. Hub records command as sent. Valve never opened (node was reconnecting). Hub thinks irrigation happened. Plants die.

**Instead:** All actuator commands publish to a command topic, node executes and publishes to ack topic, hub marks command as confirmed only when ack received. Unacked commands after timeout → alert + retry policy.

---

## Sources

**Confidence notes:** Web search and WebFetch were unavailable in this research session. The following are based on training data (cutoff August 2025) for stable, well-documented protocols and technologies.

| Claim | Confidence | Basis |
|-------|------------|-------|
| MQTT QoS levels, LWT, retained messages, persistent sessions | HIGH | MQTT 5.0 specification; Mosquitto is 20+ year stable project |
| Mosquitto ACL and password file format | HIGH | Well-documented, stable since v1.x |
| TimescaleDB hypertable and continuous aggregate syntax | HIGH | TimescaleDB 2.x documentation; stable API |
| ONNX Runtime ARM64 support | HIGH | ONNX Runtime has supported ARM64/aarch64 since 1.8; confirmed in Pi use cases pre-cutoff |
| Pi Zero 2W constraints vs Pi 5 capabilities | HIGH | Published hardware specs; widely benchmarked in IoT community |
| ESP32 OTA partition scheme | HIGH | ESP-IDF OTA documentation; core feature of ESP-IDF v5.x |
| Hub-and-spoke vs mesh topology tradeoffs | HIGH | Foundational distributed systems patterns; not subject to version drift |
| ONNX vs PyTorch runtime weight on constrained hardware | MEDIUM | Benchmarks pre-cutoff show ONNX Runtime significantly lighter; verify for current Pi 5 workloads |

**Recommended verification steps before implementation:**
- Verify Mosquitto 2.x ACL format (confirm `topic readwrite` syntax unchanged in current release)
- Verify TimescaleDB continuous aggregate syntax for current version (API changed between v1 and v2)
- Benchmark ONNX Runtime inference latency on Pi 5 with target model sizes before committing to inference schedule
