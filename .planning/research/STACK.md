# Technology Stack

**Project:** Backyard Farm Platform
**Researched:** 2026-04-01
**Research method:** Training knowledge (cutoff August 2025). Web access was unavailable during this session. All version numbers and ecosystem claims should be verified against official sources before committing to implementation. Confidence levels are assigned conservatively.

---

## Recommended Stack

### Edge Nodes (Sensor/Actuator Layer)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Raspberry Pi Zero 2 W | (hardware) | Low-cost zones — soil sensors, valve control | Runs full Linux, supports Python ecosystem, GPIO, I2C, SPI, Wi-Fi built in. 512 MB RAM is tight but workable for a polling loop + MQTT publisher |
| Raspberry Pi 4 / 5 | (hardware) | AI inference node (hub or coop node) | Needed if running llama.cpp or ONNX locally — the Zero 2 W cannot handle it. Pi 5 has 4-8 GB RAM and a faster CPU |
| ESP32 (e.g., ESP32-S3) | (hardware) | Ultra-low-power sensor leaf nodes | Good for battery-powered outlier sensors (remote soil probes). MicroPython or C++ firmware. Cannot run AI inference — data relay only |
| Python 3.11+ | language | Edge node runtime on Pi | Mature ecosystem for GPIO (RPi.GPIO, gpiozero), I2C sensor libraries (Adafruit CircuitPython), and MQTT clients. Fastest path to working hardware integration |
| MicroPython 1.22+ | language | Firmware for ESP32 leaf nodes | The standard choice for ESP32 when you want Python semantics without full Linux. Async support via uasyncio. Limited RAM (~256 KB) means no heavy libs |
| FastAPI 0.110+ | framework | Edge node HTTP API (optional local health/config endpoint) | Lightweight, async, self-documenting. Only needed if the hub needs to push config back to a node |

**What NOT to use on edge nodes:**

- **Rust on Pi** — The GPIO/sensor library ecosystem in Rust lags far behind Python. rppal exists but sensor vendor support is minimal. Use Rust only if you have a performance bottleneck you can measure, not as a default.
- **Go on Pi** — Similar gap: GPIO library ecosystem is thin. Not worth it for a sensor polling loop.
- **Node.js on Pi** — Works but the JavaScript async model is a poor fit for tight hardware loops. Python wins here.
- **Full Raspberry Pi OS Desktop** — Use Raspberry Pi OS Lite (64-bit). The desktop adds 500 MB of overhead with no benefit for a headless sensor node.
- **Arduino (ATmega-based)** — No Wi-Fi, no Python, limited to C++. Superseded by ESP32 for this use case.

---

### Hub (Central Aggregation + AI + Dashboard Server)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Raspberry Pi 5 (8 GB) or mini-PC (e.g., Intel NUC, Beelink SER) | (hardware) | Hub hardware | The Pi 5 can run Mosquitto + TimescaleDB + a small LLM for light inference. A mini-PC (x86_64, 16 GB RAM) is strongly preferred if budget allows — llama.cpp runs 3-5x faster on x86 with AVX2 |
| Python 3.11+ | language | Hub orchestration, recommendation engine glue | Consistency with edge nodes; excellent ML/AI library support |
| Docker Compose | v2.24+ | Service orchestration on hub | Keeps Mosquitto, TimescaleDB, and the app stack isolated and reproducible. No Kubernetes overhead needed at this scale |

---

### Local AI Inference

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| llama.cpp | current (gguf era, mid-2024+) | Primary LLM inference runtime on hub | Best performance-per-watt on ARM and x86 without a GPU. Runs quantized models (Q4_K_M, Q5_K_M) in 4-8 GB RAM. No cloud dependency. The underlying engine Ollama wraps |
| Ollama | 0.1.x / 0.2.x | LLM serving layer on hub | Wraps llama.cpp with a clean REST API and model management CLI. Excellent DX for pulling and running quantized open models (Llama 3, Mistral, Gemma 2). REST API makes it trivially consumable from Python |
| ONNX Runtime | 1.17+ | Lightweight model inference for non-LLM tasks (anomaly detection, time-series forecasting) | For structured sensor data tasks (is this pH pattern anomalous?), a small ONNX model will be 100x faster and use far less RAM than an LLM. Use ONNX for classification/regression, LLM for natural-language recommendations |
| TensorFlow Lite | 2.16+ | Inference on ESP32 / Pi Zero if needed | Only if you need on-device inference at the leaf node level — for example, detecting a valve failure pattern without round-tripping to hub. TFLite models can run in ~100-500 KB. Use sparingly |

**Model recommendations (quantized, hub-runnable):**

- **Llama 3.2 3B Q4_K_M** — ~2 GB RAM. Best fit for Pi 5. Can reason about sensor context and generate recommendations in natural language.
- **Gemma 2 2B Q4_K_M** — ~1.5 GB RAM. Faster than Llama 3.2 3B on ARM, slightly lower quality. Good alternative for resource-constrained hub.
- **Mistral 7B Q4_K_M** — ~4.5 GB RAM. Use only if hub has 8+ GB RAM free after other services. Meaningfully better reasoning for complex multi-zone analysis.

**What NOT to use for local AI:**

- **Ollama on edge nodes (Pi Zero 2 W / ESP32)** — Zero 2 W has 512 MB RAM. Ollama requires 4+ GB. Hard no.
- **TinyML (TensorFlow Lite Micro)** on hub — This is designed for microcontrollers (ESP32, Arduino Nano). On the hub, use full ONNX Runtime or llama.cpp instead.
- **LocalAI** — Promising but less mature than Ollama as of mid-2025. Ollama has better model support and community traction. Revisit in 2026.
- **Any cloud-backed "local" option** — Conflicts with the hard local-only constraint. Explicitly verify Ollama's network calls: it does phone home for model pulls, but inference is fully local. Pull models manually or mirror if airgap is needed.

**Confidence:** MEDIUM — Ollama and llama.cpp trajectory verified through training data to mid-2025. Version numbers should be verified at implementation time.

---

### Time-Series Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| TimescaleDB | 2.14+ (PostgreSQL 16 extension) | Primary sensor time-series store | Built on PostgreSQL, so you get full SQL, JOINs, foreign keys, and the ability to store non-time-series data (zone configs, recommendations, approval history) in the same database. Automatic chunk compression. Excellent retention policies. Runs comfortably on 2-4 GB RAM |
| SQLite (via SQLiteDict or raw sqlite3) | 3.45+ | Edge node local buffer | Each edge node writes sensor readings locally before forwarding to hub. Protects against hub downtime. Lightweight, zero-config, no daemon. Files rotate on a 24-hour window |

**Why NOT the alternatives:**

- **InfluxDB 3.x** — Moved to a proprietary license for the OSS version (Apache Arrow / Flight SQL backend). InfluxDB 2.x is still fully open source but TimescaleDB offers better query ergonomics (real SQL) and a single database for both time-series and relational data. The split between InfluxQL and Flux adds learning overhead with minimal benefit at this scale.
- **QuestDB** — Strong performer on insert throughput, excellent SQL dialect, but smaller community and ecosystem than TimescaleDB. Worth watching but not the conservative choice for a solo project.
- **Prometheus + VictoriaMetrics** — Monitoring-system databases, not general-purpose time-series stores. Poor fit for storing heterogeneous sensor payloads with custom metadata. Over-engineered for this use case.
- **Raw SQLite on hub** — Works but loses automatic partitioning, compression, and retention policies. TimescaleDB hypertables handle these transparently.

**Confidence:** MEDIUM-HIGH — TimescaleDB licensing and PostgreSQL extension model is stable and well-established. InfluxDB license change was confirmed pre-cutoff.

---

### Message Bus / Edge-to-Hub Protocol

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| MQTT (protocol) | v5.0 | Edge node to hub messaging | The standard IoT protocol. Publish/subscribe, broker-mediated, designed for unreliable networks and constrained devices. Retained messages for last-known sensor state. QoS levels for delivery guarantees |
| Eclipse Mosquitto | 2.0+ | MQTT broker (runs on hub) | The canonical open-source MQTT broker. Low memory footprint (<10 MB), battle-tested, runs as a Docker container or systemd service. No-brainer choice |
| paho-mqtt (Python) | 2.0+ | MQTT client on edge nodes and hub | The reference Python MQTT client library. Maintained by Eclipse. Async support via callbacks |
| gmqtt or aiomqtt | current | Async-native Python MQTT client | If the hub's orchestration layer is heavily async (FastAPI / asyncio), aiomqtt provides a cleaner async context manager API than paho-mqtt's callback style |

**Topic schema recommendation:**

```
farm/{node_id}/sensors/{sensor_type}     # sensor readings
farm/{node_id}/actuators/{actuator_id}/state  # current actuator state
farm/{node_id}/actuators/{actuator_id}/cmd    # command to actuator
farm/hub/recommendations/{zone_id}       # AI recommendations
farm/hub/alerts                          # system-wide alerts
```

**What NOT to use:**

- **gRPC** — Excellent for service-to-service RPC but requires persistent connections and has no broker. If the hub reboots, edge nodes need reconnect logic. MQTT's broker model handles this transparently. gRPC would be appropriate for hub-to-hub or hub-to-AI-service calls if the architecture grew larger.
- **WebSockets (raw) as the edge protocol** — Good for browser-to-hub (dashboard), bad for edge nodes. No broker, no retained messages, no QoS. Use MQTT for device communication, WebSockets for browser communication.
- **CoAP** — Designed for constrained devices where MQTT's TCP overhead matters. Relevant only if running on bare-metal microcontrollers without an OS. With MicroPython on ESP32, MQTT is easier. CoAP would apply only if you had truly battery-critical sensors needing UDP.
- **REST polling from edge to hub** — Creates tight coupling, wastes CPU on polling intervals, and loses events if the hub is temporarily down. Event-driven MQTT is the right model.
- **RabbitMQ or Kafka** — Over-engineered brokers for a home farm. Mosquitto handles thousands of messages/second with negligible overhead.

**Confidence:** HIGH — MQTT + Mosquitto is the established standard for this architecture class. paho-mqtt v2.0 API changes are real and worth noting (blocking vs async).

---

### Dashboard Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SvelteKit | 2.x (Svelte 5) | Primary web dashboard + PWA | Svelte compiles to vanilla JS — no virtual DOM overhead, smallest bundle sizes of any major framework. SvelteKit provides routing, SSR/SSG, and service worker support for PWA out of the box. Critical advantage: Svelte's reactivity model is ideal for live sensor dashboards where values update frequently |
| FastAPI | 0.110+ | Hub backend API | Python, async, OpenAPI docs auto-generated, WebSocket support built in. Consistent with edge node language. Serves sensor data to the dashboard and proxies MQTT events to WebSocket clients |
| WebSockets (via FastAPI) | native | Hub-to-dashboard live updates | Push sensor updates from hub to browser without polling. FastAPI's WebSocket support is clean. MQTT → hub → WebSocket → browser is the standard pattern |
| Vite | 5.x | Build tooling (bundled with SvelteKit) | Fast dev server HMR, excellent PWA plugin ecosystem |
| @vite-pwa/sveltekit or vite-plugin-pwa | current | PWA service worker generation | Handles cache-first assets, offline shell, and install prompts. Critical for mobile use in the yard where you might lose the Wi-Fi connection temporarily |
| Chart.js or uPlot | Chart.js 4.x / uPlot 1.6+ | Sensor data visualization | uPlot is significantly faster for dense time-series (100K+ points), Chart.js is easier to customize and has a larger ecosystem. Use uPlot for the main time-series plots, Chart.js for simpler summary charts |
| shadcn-svelte | current | UI component library | Port of shadcn/ui to Svelte. Unstyled-first, composable, no runtime overhead. Avoids the lock-in of full component kits like Material |

**What NOT to use:**

- **Next.js (React)** — Heavier bundle, virtual DOM overhead, worse reactive update model for live dashboards. React's ecosystem is larger but that breadth is irrelevant for a self-hosted local dashboard. SvelteKit is the right tool here.
- **Grafana as primary dashboard** — Tempting because it handles time-series visualization well, but it cannot serve as the UX for the recommend-and-confirm flow. Building custom panels in Grafana's plugin system is painful. Use Grafana for ops monitoring only if needed; build the farm dashboard in SvelteKit.
- **Home Assistant as the base** — HA is an excellent home automation platform but its frontend is tightly coupled to its entity/state model, which does not map cleanly to zone-aware farm data with AI recommendations. Starting from HA would mean fighting the framework constantly. Build on clean foundations.
- **Vue 3 / Nuxt** — Reasonable alternative to SvelteKit, but Svelte's compile-time approach produces smaller bundles and faster runtime for reactive dashboards. No compelling reason to prefer Vue here.
- **Plain HTML + htmx** — Works and is simple, but htmx's partial-replace model is awkward for a live dashboard with many independent updating regions. Svelte's fine-grained reactivity is a better fit.

**Confidence:** MEDIUM-HIGH for SvelteKit + FastAPI combination. Svelte 5 runes syntax was released in late 2024 — verify migration guide if using tutorials from before Svelte 5 GA.

---

### Hub Backend (Orchestration Layer)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.110+ | REST + WebSocket API | As above |
| SQLAlchemy | 2.x | ORM for TimescaleDB | Modern async support, matches FastAPI's async model |
| asyncpg | 0.29+ | Async PostgreSQL driver | Fastest Python async Postgres driver; used under SQLAlchemy or directly |
| APScheduler | 4.x (asyncio scheduler) | Cron-like scheduling for sensor polling, AI inference cycles | Lightweight in-process scheduler. Handles "run AI recommendation cycle every 30 minutes" without standing up a separate task queue |
| pydantic | v2.x | Data validation and settings | FastAPI uses it natively; also ideal for sensor reading schemas and recommendation models |

---

### Supporting Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker Compose | v2.24+ | Hub service orchestration | Single `docker-compose.yml` manages Mosquitto, TimescaleDB, FastAPI hub, Ollama, SvelteKit static files |
| Caddy | 2.7+ | Reverse proxy / local TLS | Serves the SvelteKit app and proxies to FastAPI. Auto-provisions a local self-signed cert for HTTPS, which is required for PWA install on iOS. Much simpler config than nginx |
| systemd | (OS-level) | Edge node process management | On each Pi edge node, the sensor daemon runs as a systemd service with `Restart=always`. No Docker needed on constrained edge nodes |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Edge language | Python 3.11+ | Rust | GPIO/sensor ecosystem too thin in Rust for rapid iteration; use Rust only for a specific bottleneck |
| Edge language | Python 3.11+ | Go | Same ecosystem gap as Rust for hardware I/O |
| Edge language | Python 3.11+ | Node.js | Event loop fits web APIs better than hardware loops; Python wins |
| Hub language | Python 3.11+ | TypeScript/Node | Would require separate language for AI/ML glue; Python already owns that space |
| LLM runtime | Ollama (llama.cpp) | LocalAI | LocalAI less mature; Ollama has better model pull UX and community traction |
| LLM runtime | Ollama (llama.cpp) | Hugging Face Transformers | HF Transformers requires PyTorch (~2 GB) — too heavy for Pi 5; llama.cpp is purpose-built for CPU inference |
| Time-series DB | TimescaleDB | InfluxDB 3.x | InfluxDB OSS license change; Flux query language overhead; loses SQL |
| Time-series DB | TimescaleDB | QuestDB | Smaller community, less ecosystem; strong alternative if TimescaleDB proves too heavy |
| Message bus | MQTT/Mosquitto | RabbitMQ | Massive overkill; RabbitMQ requires JVM, 512 MB+ RAM |
| Message bus | MQTT/Mosquitto | gRPC | No broker = no offline tolerance; gRPC better for service mesh, not IoT telemetry |
| Dashboard | SvelteKit | Next.js / React | Heavier runtime, virtual DOM unnecessary for local dashboard |
| Dashboard | SvelteKit | Home Assistant | HA entity model fights zone-aware farm + AI recommendation UX |
| Dashboard | SvelteKit | Grafana | Cannot serve recommend-and-confirm UX flows; visualization-only |
| Proxy | Caddy | nginx | nginx config is more complex; Caddy handles local HTTPS automatically |

---

## Hardware Platform Recommendations

### Recommended: Tiered Hardware

**Tier 1 — AI Hub (one unit)**
- Raspberry Pi 5 8 GB or x86_64 mini-PC (Beelink SER5 Pro, Intel NUC)
- Runs: Mosquitto, TimescaleDB (via Docker), FastAPI hub, Ollama
- 64 GB+ SD card or SSD; SSD strongly recommended for database I/O longevity
- Connects to home router via Ethernet (not Wi-Fi) for reliability

**Tier 2 — Zone Nodes (one per garden zone)**
- Raspberry Pi Zero 2 W (~$15) per zone
- Runs: Python sensor daemon, paho-mqtt client, SQLite local buffer, gpiozero for valve control
- Powers I2C soil sensors (SHT31 for temp/humidity, DFRobot SEN0193 for moisture, Atlas Scientific for pH/nutrients)
- Wi-Fi to home router; no Ethernet port on Zero 2 W

**Tier 3 — Remote/Battery Leaf Nodes (optional)**
- ESP32-S3 for sensors too far from a Pi node or where battery power is needed
- Runs: MicroPython, uasyncio, paho-mqtt (umqtt.simple)
- Data relay only — no inference, no valve control

**Coop Node**
- Raspberry Pi 4 2 GB (more I/O headroom for door motor driver, relay board, feed sensors)
- Runs same software stack as zone nodes

### What NOT to use:

- **Jetson Nano (original)** — EOL as of March 2024. Nvidia has superseded it with Jetson Orin Nano. Only relevant if you already own one. The Pi 5 is a better value for this use case.
- **Orange Pi / Banana Pi** — Community support and GPIO library compatibility are substantially worse than Raspberry Pi. Unless Pi supply is constrained, avoid.
- **Arduino Uno/Mega** — No Wi-Fi, no Python, C++ only. ESP32 strictly supersedes it for this use case.
- **Raspberry Pi 3B+** — Single-core equivalent performance for Python workloads; I2C driver reliability issues under load. Use Zero 2 W (cheaper, same performance class) or Pi 4.

**Confidence:** MEDIUM — Raspberry Pi hardware lineup current to mid-2025. Jetson Nano EOL confirmed. ESP32-S3 as the current flagship ESP32 variant confirmed.

---

## Installation Reference

### Hub (Docker Compose)

```bash
# TimescaleDB
docker pull timescale/timescaledb:latest-pg16

# Mosquitto
docker pull eclipse-mosquitto:2

# Ollama
docker pull ollama/ollama:latest
# Then: docker exec -it ollama ollama pull llama3.2:3b-instruct-q4_K_M

# FastAPI app
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic aiomqtt apscheduler
```

### Edge Node (Pi Zero 2 W)

```bash
# Raspberry Pi OS Lite 64-bit, then:
pip install gpiozero RPi.GPIO paho-mqtt adafruit-circuitpython-sht31d
# SQLite via stdlib — no install needed
```

### ESP32 Leaf Node (MicroPython)

```python
# Flash MicroPython 1.22+ firmware via esptool
# Libraries: umqtt.simple (bundled), uasyncio (bundled)
# No pip — use mpremote or Thonny for file transfer
```

### Dashboard (SvelteKit)

```bash
npm create svelte@latest dashboard
cd dashboard
npm install
npm install -D @vite-pwa/sveltekit
npm install chart.js uplot
npm install shadcn-svelte  # follow shadcn-svelte init docs
```

---

## Local-Only Constraint Flags

The following components have network call behaviors that must be audited:

| Component | Default Behavior | Mitigation |
|-----------|-----------------|------------|
| Ollama | Pulls models from ollama.com registry | Pull models during setup on internet-connected machine, then operate airgapped. `OLLAMA_NO_HISTORY=1` env var disables telemetry |
| Docker | Pulls images from Docker Hub | Pull all images during setup; pin to specific digest hashes in `docker-compose.yml` |
| TimescaleDB | No telemetry in OSS version | No action needed |
| Mosquitto | Fully local | No action needed |
| SvelteKit build | CDN fonts/icons if you add them | Ensure all assets are bundled locally; no CDN links in production HTML |
| paho-mqtt | Fully local | No action needed |
| APScheduler | Fully local | No action needed |

**Flag:** Ollama model management is the primary local-only risk. Establish a one-time model pull procedure during initial setup, then disable outbound from the hub at the router level if strict airgap is required.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Edge hardware (Pi tiers) | MEDIUM | Pi 5 confirmed; mini-PC recommendation is general; verify current Pi availability and pricing |
| ESP32/MicroPython | HIGH | Stable ecosystem, well-established by 2025 |
| Python edge runtime | HIGH | gpiozero, paho-mqtt, adafruit-circuitpython — all stable and actively maintained |
| Ollama / llama.cpp | MEDIUM | Trajectory confirmed; exact version numbers move fast — verify current release |
| ONNX Runtime | MEDIUM-HIGH | Stable 1.17+ release train; ARM support confirmed |
| TimescaleDB | MEDIUM-HIGH | Stable; InfluxDB license change confirmed pre-cutoff |
| MQTT / Mosquitto | HIGH | Protocol and broker are mature; paho-mqtt v2 API changes are real |
| SvelteKit / Svelte 5 | MEDIUM | Svelte 5 GA in late 2024; runes syntax is new — tutorial era matters |
| FastAPI | HIGH | Stable, widely deployed, well-maintained |
| Docker Compose v2 | HIGH | v2 is the default since 2023; v1 (docker-compose) is deprecated |

---

## Sources

All findings are from training knowledge (cutoff August 2025). No live sources were accessible during this research session.

**Recommended verification targets before implementation:**

- Ollama releases: https://github.com/ollama/ollama/releases
- TimescaleDB changelog: https://docs.timescale.com/about/latest/release-notes/
- InfluxDB licensing: https://www.influxdata.com/legal/influxdb-software-license-agreement/
- paho-mqtt v2 migration: https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
- Svelte 5 migration guide: https://svelte.dev/docs/svelte/v5-migration-guide
- MicroPython ESP32 builds: https://micropython.org/download/ESP32_GENERIC/
- Raspberry Pi 5 specs: https://www.raspberrypi.com/products/raspberry-pi-5/
- shadcn-svelte docs: https://www.shadcn-svelte.com/
