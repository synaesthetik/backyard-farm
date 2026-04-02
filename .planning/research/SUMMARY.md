# Project Research Summary

**Project:** Backyard Farm Platform
**Domain:** Distributed edge IoT — soil/flock sensing, irrigation and coop automation, local AI inference
**Researched:** 2026-04-01
**Confidence:** MEDIUM (training knowledge through August 2025; no live web access during research)

---

## Executive Summary

This is a distributed IoT platform with a well-established architectural class: hub-and-spoke edge nodes communicating via MQTT, time-series storage on the hub, and a browser-based dashboard. The core stack is well-understood — Python on edge nodes (RPi.GPIO + paho-mqtt), Mosquitto broker, TimescaleDB, FastAPI, and SvelteKit — and there is no reason to deviate from these defaults. The primary technical risks are not stack-selection risks; they are hardware integration risks concentrated in the coop door and irrigation valve control paths, and data quality risks that will corrupt the AI layer if not addressed before any model training begins.

The recommend-and-confirm AI flow is the product's defining differentiator over existing tools (FarmBot, Home Assistant, hobbyist flock apps), and none of those tools do it. However, the AI implementation should be conservative: ONNX regression and anomaly detection models for structured sensor data, not LLMs. STACK.md recommends Ollama, but ARCHITECTURE.md explicitly warns against running LLMs for sensor inference — this is a real tension that must be resolved before Phase 1. LLMs are appropriate for natural-language recommendation summaries only if the hub has sufficient RAM headroom after all other services are running; they are explicitly wrong for the sensor classification and anomaly detection core of the recommendation engine.

The biggest operational risk is silent failure: a valve stuck open, a coop door that never confirmed closed, or a sensor node that went offline six hours ago but the dashboard still shows its last reading as "current." The architecture and feature set must be built from the start around the assumption that things will fail silently, and every component must make silence loud. This is more important in early phases than AI sophistication.

---

## Cross-Cutting Findings

These findings affect multiple phases and must inform the roadmap structure, not just individual feature decisions.

### 1. Hardware failsafes are a Phase 1 hard requirement, not a later enhancement

PITFALLS flags C-1, C-2, FLAG-1, and FLAG-2 converge on the same point: coop door control and irrigation valve control require physical hardware decisions that cannot be retrofitted. Specifically:
- All irrigation valves must be normally-closed (NC) solenoids — this is a procurement decision, not a software decision
- Coop door must have physical limit switches at fully-open and fully-closed positions — this is a wiring/hardware decision
- Relay boards must be tested for active-low boot behavior before any actuator is connected (Pitfall C-4)

These are not "also do this" items. Getting them wrong causes animal mortality or flooding. They must gate Phase 1 delivery.

### 2. Stack tension: Ollama vs. ONNX for sensor inference

STACK.md recommends Ollama as the AI inference layer. ARCHITECTURE.md explicitly lists "Running LLMs for Sensor Inference" as Anti-Pattern 4 and provides a detailed warning about memory contention on the Pi 5 (4-6 GB consumed by a model, competing with TimescaleDB and the dashboard). FEATURES.md independently concludes: "Full LLM inference for recommendations is overkill and would struggle on edge hardware."

**Resolution required before Phase 1:** The AI layer must be explicitly two-tier:
- ONNX Runtime models for all structured sensor inference (irrigation, plant health, flock anomaly detection) — fast, low-memory, appropriate
- Ollama/LLM optionally, only for natural-language recommendation text generation if hub hardware (8 GB Pi 5 or mini-PC) has RAM headroom

Ollama should not be positioned as the primary inference engine. ONNX is.

### 3. Edge node offline resilience is a dependency for everything downstream

The local SQLite buffer + local rule engine on edge nodes is not optional. Without it:
- Safety rules (emergency irrigation, coop door fallback) have a single point of failure at the hub
- Sensor data is lost during any hub downtime
- The AI training dataset will have unexplained gaps that degrade model quality

This pattern must be in Phase 1. It also means edge node code has two layers to build: the sensor collection / MQTT publisher layer, and the local rule engine layer. Both are Phase 1 scope.

### 4. Sensor quality pipeline must exist before AI training begins

PITFALLS M-5 and FEATURES "Features That Are Harder Than They Look" both flag this independently. Raw sensor data cannot be fed to AI training because:
- pH probes drift 0.1-0.3 pH/month and read nonsense before calibration
- Capacitive moisture sensors require per-sensor in-situ calibration (dry/wet calibration) — factory values are meaningless
- Sensor faults (stuck at 0, stuck at 100, constant value) produce physically plausible-looking but invalid data

The quality flag pipeline (`GOOD` / `SUSPECT` / `BAD` on every reading at ingestion) is a data infrastructure requirement that must be in the hub's MQTT bridge before any AI work begins. This creates a hard sequencing dependency: data pipeline before AI layer.

### 5. The MQTT topic schema must be finalized before any node code is written

STACK.md and ARCHITECTURE.md both propose topic schemas, and they are compatible but not identical. The schema in ARCHITECTURE.md is more detailed (includes ack topics, OTA topics, heartbeat topics, zone-vs-coop distinction) and should be the canonical version. But it must be decided and documented before the first edge node is programmed — changing topic schemas across deployed nodes is operationally painful.

### 6. Silent failure is the dominant operational risk

Six of the major pitfalls (H-6, C-3, C-4, H-5, M-7, L-5) are variants of the same failure mode: the system appears operational but something critical has silently failed. The architecture's response — heartbeat monitoring, data freshness timestamps, static-reading detection, limit switch confirmation on actuator commands — must be built into the earliest phases, not added retrospectively.

---

## Key Findings

### Recommended Stack

The stack is well-converged. Python 3.11+ runs on all Pi hardware, covers the GPIO/sensor library ecosystem (gpiozero, Adafruit CircuitPython, paho-mqtt), and provides consistency between edge nodes and the hub. Docker Compose on the hub orchestrates Mosquitto, TimescaleDB, FastAPI, and (optionally) Ollama. SvelteKit + FastAPI is the dashboard stack. There are no controversial choices.

**Critical version/procurement notes:**
- paho-mqtt v2.0 has a breaking API change from v1.x — use aiomqtt if the hub service is async-heavy
- Svelte 5 (runes syntax) is the current GA; tutorials predating late 2024 use the old syntax
- TimescaleDB continuous aggregate syntax changed between v1 and v2 — verify against v2.14+ docs
- Pi relay HATs: test cold-boot relay state before connecting any actuator (extremely common failure mode per Pitfall C-4)

**Core technologies:**
- Python 3.11+ on all Pi hardware — mature GPIO/sensor ecosystem, consistency across tiers
- MQTT 5.0 + Eclipse Mosquitto — purpose-built IoT pub/sub, QoS levels match use case, LWT for node health
- TimescaleDB 2.14+ — Postgres-compatible time-series with continuous aggregates, real SQL, no cloud dependency
- FastAPI 0.110+ — async Python API, WebSocket support, OpenAPI auto-docs
- SvelteKit 2.x (Svelte 5) — compile-time reactivity ideal for live sensor dashboards, smallest bundle, PWA support
- ONNX Runtime 1.17+ — primary inference runtime for sensor classification/regression (not Ollama)
- Ollama (optional) — LLM serving only if hub has RAM headroom; not the primary AI engine
- Docker Compose v2.24+ — hub service orchestration
- Caddy 2.7+ — reverse proxy with automatic local HTTPS (required for PWA install on iOS)
- SQLite (stdlib) — edge node local buffer, no daemon, survives power loss

**Hardware tiers (recommended):**
- Hub: Pi 5 8GB or x86_64 mini-PC (Beelink SER5 Pro / Intel NUC) — mini-PC preferred if budget allows, 3-5x faster LLM inference
- Zone nodes: Pi Zero 2 W per garden zone — GPIO, I2C, Wi-Fi, Python; tight at 512 MB RAM but workable for sensor loop + MQTT
- Coop node: Pi 4 2GB — more I/O headroom for motor driver + relay board + multiple sensors
- Remote/battery leaf nodes (optional): ESP32-S3 with MicroPython — ultra-low power, data relay only

### Expected Features

**Must have in V1 (table stakes):**
- Live sensor readings per zone (moisture, pH, temp) with freshness timestamps
- 7-day and 30-day sensor history graphs
- Threshold-based alerts with debounce (moisture, pH extremes, temperature extremes)
- Manual irrigation control from dashboard
- Zone configuration with plant type, soil type, and irrigation parameters
- Zone health status (composite green/yellow/red score)
- pH calibration workflow with due-date tracking (calibration is not optional)
- Coop door automation (astronomical clock: lat/long sunrise/sunset) with hard time limits as safety backstop
- Coop door status with limit switch confirmation and stuck-door alert
- Feed and water level monitoring with low alerts
- Daily egg count entry and production trend chart (actual vs. expected)
- Production drop alert (3-day rolling average deviation against breed/age/daylight model)
- Single overview screen covering all zones + flock
- P0/P1 alert bar with grouping and de-duplication
- Recommendation queue with approve/reject, explanation, and supporting sensor values
- System/node health status (heartbeat, offline detection, data freshness indicator)
- Offline-capable PWA (service worker, usable on phone in the yard)
- AI-recommended sensor-feedback irrigation (irrigate to target VWC) pending farmer approval

**Should have as differentiators (V1 if capacity, otherwise early V2):**
- Seasonal egg production model (day-length factor, breed lay-rate baseline, age decline curve)
- Feed consumption rate tracking (requires load cell sensor; enables illness-signal alert in V2)
- ntfy or equivalent self-hosted push notification backend (in-app alerts sufficient for V1 baseline)
- Per-zone soil type configuration feeding into AI recommendation thresholds

**Defer to V2:**
- ML-predicted (LSTM/gradient-boosted) irrigation scheduling — needs 4+ weeks of training data to be meaningful; build the pipeline first, train the model later
- Nutrient/EC sensor integration — sensors are expensive, unreliable, and require frequent maintenance; validate need after V1 is running
- Per-rejection feedback tagging — collect implicit approval/rejection signal first; reason tagging adds friction
- Behavioral anomaly detection for flock — requires additional hardware (motion sensors); V2
- Zone-to-zone comparison analytics — data needs to accumulate first
- Frost prediction with pre-emptive alerts — requires weather integration
- Companion planting guidance via OpenFarm — low priority, not actionable

**Anti-features (explicitly never build in V1):**
- Fully autonomous irrigation without approval
- Cloud sync or remote access
- Computer vision / camera plant health
- External push notifications via Firebase/APNs

### Architecture Approach

The system is two-tier hub-and-spoke: edge nodes are autonomous sensor collectors and actuator controllers; the hub is the aggregation, intelligence, and presentation layer. Edge nodes operate independently when the hub is unreachable (local SQLite buffer, local rule engine for emergency actions). All AI inference runs on the hub, not on edge nodes. The MQTT broker on the hub mediates all node-to-hub communication. The dashboard communicates with the hub via REST (CRUD, history) and WebSocket (live sensor feed, recommendation push). The topic schema in ARCHITECTURE.md is the canonical reference.

**Major components:**
1. Edge node sensor daemon — polls sensors, writes to local SQLite, publishes via MQTT, runs local rule engine for emergency actuator triggers
2. Mosquitto broker — routes all MQTT traffic; ACL per node identity
3. Hub MQTT bridge — subscribes to all farm topics, validates readings, applies quality flags, writes to TimescaleDB
4. TimescaleDB — time-series storage with continuous aggregates for hourly/daily rollups; also stores recommendations, actuator events, and calibration state
5. AI orchestrator — scheduled ONNX inference for zone health, irrigation, and flock anomaly detection; generates recommendations; deduplicates pending queue
6. FastAPI hub — REST + WebSocket API; serves dashboard; handles recommendation approve/reject and command routing
7. SvelteKit PWA — single-page dashboard with live sensor updates via WebSocket; offline-capable service worker; mobile-first

**Security model:** JWT + Mosquitto ACL. Single shared passphrase for the dashboard. Per-node MQTT credentials with ACL rules preventing cross-zone topic access. HTTPS via Caddy with local cert (required for iOS PWA install). No OAuth, no mTLS — correctly sized for a single-user LAN system.

### Critical Pitfalls

1. **Coop door has no hardware position confirmation** — Implement physical limit switches at fully-open and fully-closed positions. After every open/close command, poll the appropriate limit switch for up to 60 seconds. If not confirmed, alert and hold. Software-only control is a predator-kill risk.

2. **Irrigation valves are not normally-closed** — Procure only NC solenoid valves. A normally-open valve (or relay that defaults open at boot) creates a flooding risk on any power loss, software crash, or reboot. This is a procurement decision that cannot be fixed in software later.

3. **Relay active-low boot state fires actuators during Pi initialization** — Test every relay board's cold-boot state before connecting any valve or actuator. Most cheap Pi relay HATs are active-low: GPIO floating at boot momentarily fires the relay. Add a GPIO initialization service that runs early in the boot sequence and drives all relay pins to the deactivated state.

4. **AI training on raw sensor data corrupts the model** — Never feed raw sensor readings to model training. The MQTT bridge must apply quality flags at ingestion (`GOOD` / `SUSPECT` / `BAD`) before data enters TimescaleDB. pH and moisture sensors require per-sensor in-situ calibration workflows before any data they produce can be trusted. Train only on `GOOD`-flagged data.

5. **Silent node failure looks like everything is fine** — Implement heartbeat monitoring (alert if node misses 3 consecutive 60-second heartbeats), data freshness timestamps on every displayed reading (flag as stale if > 5 minutes old), and static-reading detection (flag if sensor returns same value for 30+ consecutive readings). Build these into Phase 1, not as a later monitoring pass.

6. **SD card corruption kills an edge node silently** — Use high-endurance SD cards (Samsung Pro Endurance). Design edge nodes as stateless: all authoritative configuration and calibration data lives on the hub and is pushed to nodes; nodes can be re-imaged and fully reconfigured from the hub without manual intervention.

---

## Implications for Roadmap

### Suggested Phase Structure

The feature dependency tree in FEATURES.md and the architectural component boundaries in ARCHITECTURE.md converge on a natural phase ordering. Hardware failsafe requirements from PITFALLS further constrain what must ship together.

---

#### Phase 1: Hardware Foundation and Sensor Pipeline

**Rationale:** Everything else — alerts, dashboards, AI, recommendations — depends on trustworthy sensor data flowing from edge nodes to the hub. This phase produces no user-visible features except raw sensor readings and node health status, but it is the foundation every subsequent phase builds on. Hardware failsafe decisions (NC valves, limit switches, relay boot behavior) must be resolved here because they are procurement and wiring decisions, not software decisions.

**Delivers:**
- Hardware selected, procured, and wired (hub, zone nodes, coop node)
- NC solenoid valves confirmed for all irrigation zones
- Coop door limit switches wired and tested
- Relay board boot behavior documented and mitigated
- Edge node sensor daemon: polls sensors, writes to local SQLite buffer, publishes via MQTT
- Local rule engine on edge nodes: emergency irrigation trigger and coop door fallback (hardware-enforced safe states)
- Mosquitto broker on hub with per-node ACL credentials
- Hub MQTT bridge: subscribes, validates, applies quality flags, writes to TimescaleDB
- TimescaleDB schema: sensor_readings hypertable with quality flags, actuator_events, continuous aggregates
- Heartbeat monitoring and node health alerting
- Static IP assignments for all nodes; hub configured as NTP server for LAN
- Minimal dashboard: live sensor readings with freshness timestamps and node online/offline status

**Must avoid:** C-1 (coop door no confirmation), C-2 (runaway irrigation), C-3 (SD card as authoritative store), C-4 (relay boot state), H-5 (power outage undefined state), H-6 (silent failure)

**Research flag:** Phase 1 requires hardware-in-hand answers (see "Open Hardware Questions" below). Do not finalize the software sensor driver layer until specific sensor models are chosen — calibration workflow design depends on the sensor interface.

---

#### Phase 2: Actuator Control, Alerts, and Dashboard V1

**Rationale:** With trustworthy sensor data flowing, actuator control and the alert surface can be built. The recommend-and-confirm flow can be introduced for irrigation at this phase — the AI is rule-based for now (thresholds and schedules), not ONNX models, but the UX flow is the same. Getting the approval UX right matters more than ML sophistication.

**Delivers:**
- Manual irrigation control from dashboard (zone valve open/close with hub command routing)
- Threshold-based irrigation recommendations with approve/reject UX (rule-based, not ML)
- Sensor-feedback irrigation loop: irrigate to target VWC, stop on threshold reached
- Single-zone-at-a-time invariant enforced in hub irrigation controller (prevents simultaneous zone conflict)
- Coop door control: astronomical clock schedule with configurable offsets, manual override, limit switch confirmation, stuck-door alert
- Feed/water level display and low-level alerts
- P0/P1 alert bar with grouping, debounce, and hysteresis
- Alert suppression after action (cool-down window post-irrigation to prevent storm)
- Zone health composite score (green/yellow/red derived from moisture, pH, temperature)
- Recommendation queue UI: approve/reject with explanation and supporting sensor values shown
- SvelteKit PWA with service worker and offline shell

**Must avoid:** M-3 (simultaneous zone valve conflict), F-L5 (PWA stale data — data freshness display is Phase 1 but PWA cache strategy is Phase 2), L-3 (cron drift for door schedule — use absolute-time scheduling), L-4 (DST causes door skip — UTC internally everywhere)

**Research flag:** Standard patterns for threshold alerting and irrigation scheduling (well-documented). Recommend-and-confirm UX warrants a focused design pass before implementation — the flow is the product's core differentiator and getting it wrong erodes farmer trust.

---

#### Phase 3: Flock Management and Egg Production Model

**Rationale:** Flock management is architecturally independent of garden zones (different sensors, different data model, different alert logic) and can be built in parallel or sequentially after Phase 2. Sequencing it after Phase 2 lets the actuator control and alert patterns from Phase 2 be reused (coop door was already in Phase 2; this phase adds the production model and flock health layer).

**Delivers:**
- Daily egg count entry form
- Egg production trend chart (actual vs. expected)
- Expected production model: flock size × breed lay rate × age factor × daylight factor
- Production drop alert (3-day rolling average below 75% of expected)
- Feed consumption rate display (if load cell sensor — enables illness signal in V2)
- Flock configuration: breed, age, flock size, supplemental lighting state
- Unified overview screen: all garden zones + flock status in one view

**Must avoid:** M-4 (coop environment kills sensors — conformal coating, IP65 enclosures, quarterly maintenance schedule established)

**Research flag:** Breed-specific lay rate tables exist in agricultural extension literature (HIGH confidence). Day-length calculation using NOAA solar algorithm is well-documented. The age decline curve coefficients may need empirical tuning after initial data accumulates.

---

#### Phase 4: ONNX AI Layer and Recommendation Engine

**Rationale:** This phase builds the ML-backed recommendation engine on top of the validated sensor data pipeline from Phase 1. A minimum of 2-4 weeks of clean (quality-flagged `GOOD`) sensor data must exist before ONNX model training is meaningful. Sequencing AI after data pipeline ensures the training dataset is not corrupted by uncalibrated sensors or missing quality flags. The recommendation UX already exists from Phase 2 — this phase upgrades the engine behind it.

**Delivers:**
- ONNX Runtime models for: zone health scoring, irrigation schedule optimization, flock production anomaly detection
- Feature aggregation service on hub: assembles recent sensor windows per zone for inference input
- Scheduled inference triggers: zone health every 15 min, irrigation every 1 hour, flock health every 30 min
- Event-triggered inference: threshold crossing in any zone triggers immediate re-inference for that zone
- Recommendation deduplication: suppress if pending recommendation of same type exists; back-off window after rejection
- AI learning baseline: log every recommendation with sensor context; track approval/rejection rate per recommendation type; surface threshold adjustment suggestions after 50+ data points
- Model maturity indicator in UI: "Learning in progress (12 approvals so far)" — manages user expectation during cold start

**Must avoid:** H-3 (AI inference latency competing with sensor collection — inference on hub only, never on edge nodes; sensor alerts evaluated by rule engine, not AI), M-5 (AI trained on raw data — only `GOOD`-flagged data used), ARCHITECTURE Anti-Pattern 4 (LLMs for sensor inference — use ONNX)

**Research flag:** Specific ONNX model architectures for sensor time-series (random forest vs. gradient boosted vs. small neural network) need empirical selection — this is a LOW confidence area. Plan a model selection spike before full implementation. Benchmark ONNX inference latency on the actual hub hardware at operating temperature before committing to inference schedule intervals.

---

#### Phase 5: Operational Hardening and V2 Prep

**Rationale:** A working system in daily use will surface operational issues that no amount of upfront design catches: sensor drift patterns, actual SD card failure modes, network reliability quirks, edge cases in the coop door schedule at extreme seasons. This phase addresses those findings, adds the OTA update system for edge nodes, and lays groundwork for V2 features.

**Delivers:**
- OTA update system: hub-served packages, MQTT-triggered, SHA256 verified, staged rollout policy
- Node re-image and reconfigure automation from hub (zero-manual-steps recovery)
- pH calibration workflow with in-app reminders, calibration offset storage, and drift detection
- Sensor calibration management: per-sensor `dry_value` / `wet_value` / `temperature_coefficient` stored on hub, applied at ingestion
- System update discipline: pinned dependency versions, lockfiles, staged rollout procedure documented
- ntfy or equivalent self-hosted push notification integration (optional but recommended)
- Retention policy configuration: raw sensor data 90 days, hourly rollups 2 years
- Hub UPS setup guidance and graceful shutdown procedure on power loss

**Research flag:** Standard operational patterns. OTA for ESP32 nodes uses ESP-IDF OTA partition scheme — well-documented. No research-phase needed; implementation follows ARCHITECTURE.md OTA section.

---

### Phase Ordering Rationale

- **Phase 1 before everything:** The sensor pipeline is the critical path. No alert, recommendation, dashboard, or AI feature is meaningful without it. Hardware failsafe decisions are irreversible and must be made before Phase 1 hardware is purchased.
- **Phase 2 before Phase 4:** The recommend-and-confirm UX must exist and be validated by a farmer using rule-based recommendations before adding ML complexity behind it. If the UX is wrong, ML sophistication doesn't save it.
- **Phase 3 is parallelizable with Phase 2:** Garden and flock management are architecturally independent. A team could split them. Sequenced here for a solo developer's linear execution.
- **Phase 4 is gated on data maturity:** Training meaningful ONNX models requires clean historical data. Starting Phase 4 before 4 weeks of quality-flagged data exist is wasted effort. Use the gap between Phase 2/3 completion and Phase 4 start to accumulate data.
- **Phase 5 is continuous:** Operational hardening does not wait for Phase 5. Heartbeat monitoring (Phase 1), data freshness display (Phase 2), and calibration reminders (Phase 5 formalization) should be introduced incrementally. Phase 5 is the formalization pass, not the first introduction.

---

### Research Flags

**Needs deeper research or hardware-in-hand validation before implementation:**
- **Phase 1 — Sensor selection:** Specific sensor models (moisture, pH, temperature, feed weight, water level, coop door limit switch, relay board) are undecided. The calibration workflow design, driver implementation, and quality flag thresholds all depend on the specific hardware chosen. This is the most significant open question in the entire project.
- **Phase 1 — Relay board behavior:** Must be tested on actual hardware before any actuator is connected. Not researchable without the board in hand.
- **Phase 4 — ONNX model selection:** Random forest vs. gradient boosted vs. small neural network for sensor time-series is LOW confidence. Needs a model selection spike on actual data.
- **Phase 4 — Inference latency on target hardware:** Benchmark ONNX runtime on the actual hub hardware at operating temperature before committing to inference schedule. A model that runs in 50ms on a developer machine may run in 2s on a Pi 5 in an outdoor enclosure.

**Standard patterns (skip research phase, follow existing docs):**
- **Phase 2 — Threshold alert logic, debounce, hysteresis:** Well-established IoT patterns, HIGH confidence in FEATURES.md and PITFALLS.md guidance
- **Phase 2 — MQTT topic schema and ACL:** Fully specified in ARCHITECTURE.md; follow it
- **Phase 3 — Coop door astronomical clock:** NOAA solar algorithm is public domain, well-documented; HIGH confidence
- **Phase 3 — Egg production model:** Poultry science factors (breed lay rate, age curve, daylight) are HIGH confidence from agricultural extension literature
- **Phase 5 — OTA update system:** ESP-IDF OTA partition scheme is well-documented; hub-served HTTP + MQTT trigger pattern is specified in ARCHITECTURE.md

---

## Decisions Required Before Phase 1 Can Start

These are blocking decisions — they affect procurement, wiring, or software architecture in ways that cannot be easily changed later.

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **Hub hardware: Pi 5 vs. mini-PC** | Pi 5 8GB (~$80) sufficient for ONNX; x86 mini-PC (Beelink SER5 Pro, ~$200-300) 3-5x faster for any LLM use, better I/O | Mini-PC if budget allows; Pi 5 is viable if LLM use is ruled out |
| 2 | **Zone node hardware: Pi Zero 2 W vs. ESP32-S3** | Pi Zero 2 W: full Linux, Python, I2C GPIO; ESP32-S3: ultra-low power, MicroPython, data relay only | Pi Zero 2 W for zones that need valve control (GPIO relay); ESP32-S3 only for battery-powered remote sensors with no actuators |
| 3 | **Soil moisture sensor model** | Capacitive sensors (multiple vendors); quality varies dramatically; per-sensor in-situ calibration required regardless | Choose one model and stick to it across all zones — different batches require separate calibration curves, same model simplifies the software |
| 4 | **pH sensing approach: continuous in-soil vs. periodic manual** | Continuous: deployed sensor, drifts every 2-4 weeks, high maintenance; Periodic: insert probe when needed, more accurate, less data | Periodic point measurement recommended for V1 — the system can accept manual pH entries alongside the automated sensors; continuous pH adds maintenance burden before value is proven |
| 5 | **Coop door actuator type** | Linear actuator with limit switches (recommended); DC gear motor with encoder; commercial coop door controller with no external API | Linear actuator with physical limit switches is the only option compatible with the required confirmation-loop architecture |
| 6 | **Feed level sensor: load cell vs. ultrasonic vs. float** | Load cell: continuous consumption rate, enables health signal, requires tare drift management; Ultrasonic: non-contact, good for hoppers; Float: binary only | Load cell strongly preferred — consumption rate is the most valuable early health signal for flock anomaly detection |
| 7 | **AI stack confirmation: ONNX-primary or Ollama-primary** | ONNX for sensor inference (fast, low-memory, correct); Ollama for natural-language summaries only if hub has RAM headroom | Confirm ONNX as primary inference engine before any AI code is written. Ollama is optional and must not compete with TimescaleDB and the dashboard for RAM on the hub |

---

## Open Hardware Questions (Need Hardware In Hand)

These questions cannot be answered by research — they require physical testing.

1. **What is the cold-boot relay state of the specific relay board chosen?** This determines whether a GPIO initialization service is needed and how urgently.
2. **What are the actual ADC output ranges (dry/wet) for the chosen moisture sensor in the actual soil of each garden zone?** Factory spec sheets are useless; only in-situ calibration matters.
3. **Does the coop door linear actuator have built-in limit switches, or must they be added externally?** This affects wiring complexity significantly.
4. **What is ONNX Runtime inference latency for a candidate model (e.g., a small random forest or gradient-boosted model with ~50 features) on the chosen hub hardware?** Must be measured at operating temperature.
5. **What is the actual thermal behavior of the hub hardware in the intended outdoor (or indoor-shed) enclosure?** Thermal throttling at 70-80°C on a Pi 5 is not theoretical.
6. **Can the coop door node (Pi 4 or Zero 2 W) reliably power a relay board + motor driver simultaneously from the same power supply?** Inrush current from a door motor can cause voltage droop that resets the Pi.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (software) | MEDIUM-HIGH | FastAPI, SvelteKit, TimescaleDB, Mosquitto are stable and well-documented. Svelte 5 runes syntax is new (late 2024) — verify tutorials. paho-mqtt v2 API changed. |
| Stack (hardware) | MEDIUM | Pi 5 and Zero 2 W specs confirmed. Specific sensor models undecided — this is the biggest gap. |
| Features | MEDIUM-HIGH | Table stakes features are well-defined. Agricultural thresholds (VWC, pH, poultry production) are HIGH confidence from published standards. Specific sensor model limitations are MEDIUM. |
| Architecture | HIGH | Hub-and-spoke MQTT topology is a mature, well-established IoT pattern. TimescaleDB schema, MQTT topic design, and offline resilience patterns are all solid. |
| Pitfalls | MEDIUM-HIGH | Hardware failure modes (SD card, relay boot, pH drift, capacitive sensor calibration) are well-documented. Specific component behaviors need hardware verification. |

**Overall confidence:** MEDIUM-HIGH for software architecture and feature design. MEDIUM for hardware selection and AI model specifics, which are the two areas requiring hardware-in-hand validation.

### Gaps to Address

- **Sensor selection is the largest unresolved decision.** The calibration workflow, quality flag thresholds, and driver implementation all depend on specific sensor models. This should be the first task in Phase 1 — before any software is written.
- **ONNX model architecture for sensor time-series** is LOW confidence. Plan a model selection spike using 4+ weeks of collected data before committing to a specific model architecture.
- **iOS PWA push notification behavior** is evolving (improved in iOS 16.4+, full in iOS 17+). Test early on actual iOS hardware to confirm "add to home screen" requirement and service worker behavior.
- **ntfy self-hosted push** is MEDIUM confidence — solid as of 2025 but verify current setup requirements and iOS compatibility.
- **Ollama on Pi 5 memory footprint alongside other services** is MEDIUM confidence. If LLM natural-language summaries are desired, measure actual RAM usage under load before committing to that feature.

---

## Sources

### HIGH confidence (published standards and stable specifications)
- MQTT 5.0 specification and Mosquitto documentation — protocol semantics, QoS levels, LWT, ACL format
- TimescaleDB 2.x documentation — hypertable syntax, continuous aggregate API (confirm v2.14+ syntax before use)
- FAO Irrigation and Drainage Paper 56 (Penman-Monteith ET standard)
- USDA NRCS soil moisture guides — VWC threshold recommendations
- University agricultural extension publications (Cornell, UC Davis, Penn State) — soil pH thresholds
- University of Georgia and Penn State Poultry Extension — production decline thresholds
- NOAA Solar Calculator algorithm (public domain) — astronomical clock for coop door
- ESP-IDF OTA documentation — partition scheme for ESP32 firmware updates
- Raspberry Pi hardware specifications — Pi 5, Zero 2 W, Pi 4 thermal thresholds

### MEDIUM confidence (training knowledge through August 2025; verify at implementation time)
- Ollama and llama.cpp release trajectory — verify current version at implementation
- ONNX Runtime ARM64 benchmark data — verify on actual target hardware
- SvelteKit 2.x / Svelte 5 documentation — runes syntax is new; tutorials predate GA
- FarmBot and Home Assistant feature set — actively developed; gaps identified are structural design choices
- iOS PWA push notification support (iOS 16.4+/17+) — verify on actual device
- ntfy self-hosted push — verify current iOS compatibility
- Coop door failure mode community patterns — consistent across forums but specific product behaviors not verified

### LOW confidence (needs validation before implementation)
- Specific ONNX model architecture for sensor time-series inference (random forest vs. gradient boosted vs. neural network) — needs empirical selection
- Nutrient/EC sensor market — actively changing; verify specific sensor options before committing
- FarmBot self-hosting quality — documentation quality is actively changing per community reports

---

*Research completed: 2026-04-01*
*Ready for roadmap: yes*
