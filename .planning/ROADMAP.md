# Roadmap: Backyard Farm Platform

## Overview

Seven phases transform an unboxed pile of hardware into a self-hosted farm dashboard where
sensor data flows reliably from edge nodes to the hub, irrigation and coop automation run
with farmer approval, flock health is tracked alongside garden zones on a single screen, and
ONNX models replace rule-based logic behind the same recommend-and-confirm UX. The final two
phases ensure anyone can build and use the system: a complete hardware shopping list with
wiring diagrams, and an interactive tutorial with full reference documentation. Phase 1 is
entirely about trust — trustworthy hardware, trustworthy sensor data, trustworthy silence
detection. Nothing else is possible without it.

## Phase Dependency Diagram

```
Phase 1: Hardware Foundation + Sensor Pipeline
         |
         |-- Sensor data flowing, quality-flagged, hub operational
         |-- Hardware failsafes confirmed (NC valves, limit switches, relay boot)
         |
         v
Phase 2: Actuator Control, Alerts, and Dashboard V1
         |
         |-- Recommend-and-confirm UX live (rule-based engine)
         |-- Irrigation and coop controlled from dashboard
         |-- 4+ weeks of GOOD-flagged sensor data accumulating
         |
         v
Phase 3: Flock Management and Unified Dashboard
         |             (can overlap with Phase 2 once coop node is stable)
         |-- Egg production model, flock health alerts, unified overview screen
         |
         +----------------------------+
                                      |
                                      v
                            Phase 4: ONNX AI Layer
                                      |
                                      |-- DATA MATURITY GATE:
                                      |   4+ weeks of GOOD-flagged sensor data
                                      |   required before model training begins
                                      |
                                      v
                            Phase 5: Operational Hardening
                                      |
                                      |-- pH calibration workflows, push notifications,
                                      |   data retention policies, ntfy integration
                                      |
                                      v
                            Phase 6: Hardware Shopping List and Wiring Diagrams
                                      |
                                      |-- Every component, connection, and pin documented
                                      |-- Smoke test procedures for each subsystem
                                      |
                                      v
                            Phase 7: Interactive Tutorial and User Documentation
                                      |
                                      |-- In-app tutorial, full reference docs,
                                      |   troubleshooting guide, auto-built from source
```

**Sequencing rationale:**
- Phase 1 before everything: the sensor pipeline is the critical path for all other work.
- Phase 2 before Phase 4: the recommend-and-confirm UX must exist and be validated with
  rule-based logic before ML complexity is introduced behind it.
- Phase 3 is largely independent of Phase 2 (different sensors, different data model) but
  is sequenced after it for linear solo-developer execution; the coop node from Phase 2
  is a prerequisite for flock sensor data.
- Phase 4 has a hard data maturity gate — it cannot start until 4+ weeks of GOOD-quality
  sensor data exists from Phase 1. Use the Phase 2/3 execution window to accumulate data.
- Phase 5 is formalization: operational patterns (heartbeats, freshness, calibration) are
  introduced incrementally in earlier phases; Phase 5 systematizes and completes them.

---

## Phases

- [ ] **Phase 1: Hardware Foundation and Sensor Pipeline** - Trustworthy sensor data flowing from edge nodes to hub; all hardware failsafes confirmed
- [x] **Phase 2: Actuator Control, Alerts, and Dashboard V1** - Farmer monitors zones and flock, controls irrigation and coop, and acts on rule-based recommendations from a PWA dashboard (completed 2026-04-10)
- [x] **Phase 3: Flock Management and Unified Dashboard** - Complete flock tracking and single unified overview screen covering all zones and flock (completed 2026-04-15)
- [ ] **Phase 4: ONNX AI Layer and Recommendation Engine** - ML-backed recommendations replace rule-based engine behind the existing recommend-and-confirm UX
- [ ] **Phase 5: Operational Hardening** - pH calibration workflows, push notifications, data retention policies, and sensor calibration management
- [ ] **Phase 6: Hardware Shopping List and Wiring Diagrams** - Complete BOM, wiring diagrams for every connection, and smoke test procedures
- [ ] **Phase 7: Interactive Tutorial and User Documentation** - In-app tutorial, full reference docs, and troubleshooting guide

---

## Phase Details

### Phase 1: Hardware Foundation and Sensor Pipeline

**Goal**: Trustworthy sensor data flows from every edge node to the hub with quality flags, node health is visible on a minimal dashboard, and all hardware failsafes are confirmed before any actuator is connected.

**Depends on**: Nothing (first phase)

**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, INFRA-09, ZONE-01, ZONE-02, ZONE-03, ZONE-04, IRRIG-03, COOP-04, UI-04, UI-07

**Hardware Procurement Checklist (gate before any software work):**
- All irrigation solenoid valves confirmed normally-closed (NC) — not normally-open
- Coop door actuator confirmed as linear actuator with physical limit switches at fully-open and fully-closed positions
- Relay board(s) procured and cold-boot relay state tested BEFORE connecting any valve or actuator — if active-low, a GPIO initialization service must be written and confirmed working first
- High-endurance SD cards (Samsung Pro Endurance or equivalent) in all Pi nodes
- Hub hardware selected: Pi 5 8GB or x86_64 mini-PC; SSD strongly preferred over SD card for TimescaleDB I/O
- Hub connects to router via Ethernet (not Wi-Fi)
- Static IP assigned to hub; hub configured as NTP server for LAN

**Success Criteria** (what must be TRUE):
  1. Live soil moisture, pH, and temperature readings for every configured garden zone appear on the dashboard with freshness timestamps; readings older than 5 minutes are visually flagged as stale
  2. Each sensor reading is stored in TimescaleDB with a quality flag (GOOD / SUSPECT / BAD); the hub's MQTT bridge applies calibration offsets before writing
  3. If any edge node misses 3 consecutive 60-second heartbeats, the system health panel shows that node as offline within 90 seconds
  4. If a sensor returns the same value for 30+ consecutive readings, that sensor is flagged as potentially stuck in the dashboard
  5. The hub dashboard is accessible from any browser on the LAN via HTTPS; the URL is stable and does not require accepting a certificate warning on subsequent visits

**Plans**: 8 plans

Plans:
- [x] 01-01-PLAN.md — Hub service stack (Docker Compose: Mosquitto, TimescaleDB, FastAPI, Caddy, SvelteKit scaffold)
- [x] 01-02-PLAN.md — MQTT topic schema, per-node ACL credentials, and Mosquitto configuration
- [x] 01-03-PLAN.md — Edge node sensor daemon (polling loop, SQLite buffer, MQTT publish with reconnect flush)
- [x] 01-04-PLAN.md — Edge node local rule engine (emergency irrigation shutoff, coop door hard-close)
- [x] 01-05-PLAN.md — Hub MQTT bridge (quality flags, calibration offsets, stuck detection, heartbeat tracking, WebSocket manager)
- [x] 01-06-PLAN.md — Minimal dashboard (zone cards, sensor values, quality badges, stale/stuck indicators, system health panel)
- [x] 01-07-PLAN.md — Gap closure: Fix WebSocket routing (Caddyfile /ws/dashboard -> api:8000)
- [x] 01-08-PLAN.md — Gap closure: Dashboard component unit tests (SensorValue, ZoneCard, NodeHealthRow)

**UI hint**: yes

---

### Phase 2: Actuator Control, Alerts, and Dashboard V1

**Goal**: The farmer can monitor all garden zones, manually control irrigation and the coop door, and act on rule-based recommendations from the recommend-and-confirm queue — all from a mobile-friendly PWA. This phase delivers the product's core UX differentiator; the recommendation engine is rule-based for now, but the approve/reject flow is production-quality and sets the pattern for Phase 4.

**Depends on**: Phase 1

**Requirements**: ZONE-05, ZONE-06, IRRIG-01, IRRIG-02, IRRIG-04, IRRIG-05, IRRIG-06, COOP-01, COOP-02, COOP-03, COOP-05, COOP-06, COOP-07, AI-01, AI-02, AI-04, AI-05, UI-02, UI-03, UI-05, UI-06, NOTF-01, NOTF-02

**Critical design note — recommend-and-confirm UX:**
This is the product's defining feature. The recommendation queue must show: action description, supporting sensor values with context, and explanation of why the action is recommended. Approve sends a command through the hub to the edge node actuator and waits for the ack. Reject starts the back-off window for that recommendation type. The UX must be fast enough to use while standing in the yard. Design this flow before implementing it.

**Success Criteria** (what must be TRUE):
  1. A farmer can open or close an irrigation valve for any zone from the dashboard; the command routes hub → edge node → relay and the zone's irrigation status updates within 5 seconds; the hub prevents opening a second zone while one is already open
  2. A recommendation to irrigate zone X appears in the recommendation queue when zone X's VWC drops below its configured low threshold; the farmer can approve (triggering the sensor-feedback irrigation loop) or reject (starting a configurable back-off window); duplicate recommendations for the same zone and type are suppressed while one is pending
  3. The coop door opens at calculated sunrise and closes at calculated sunset based on configured lat/long; the dashboard shows door state as open / closed / moving / stuck; a stuck-door alert fires if the expected limit switch is not reached within 60 seconds of a command
  4. A P0/P1 alert bar is visible on every screen; low feed, low water, stuck door, and node-offline alerts appear there with debounce and hysteresis — the same alert does not fire repeatedly for the same sustained condition
  5. The dashboard installs as a PWA on iOS and Android and is usable on a phone screen in the yard; sensor data shown is always fresh or clearly flagged as stale

**Plans**: 7 plans

Plans:
- [x] 02-01-PLAN.md — Data contracts, actuator command endpoints, zone config store, MQTT ack flow, single-zone invariant
- [x] 02-02-PLAN.md — Rule engine, alert engine (debounce/hysteresis), zone health score, sensor-feedback irrigation loop
- [x] 02-03-PLAN.md — Coop scheduler (astral), bridge integration, history endpoint, recommendation approve/reject endpoints
- [x] 02-04-PLAN.md — Frontend foundation: routing, layout, TabBar, AlertBar, Toast, CommandButton, HealthBadge, WS store extension
- [x] 02-05-PLAN.md — Feature pages: zone detail (irrigation + charts), coop panel, recommendation queue (uPlot install)
- [x] 02-06-PLAN.md — PWA service worker, manifest, component tests, build verification, human sign-off
- [ ] 02-07-PLAN.md — Gap closure: fix approve/reject 503 by proxying API to bridge internal HTTP server (AI-01, AI-05, IRRIG-05)

**UI hint**: yes

---

### Phase 3: Flock Management and Unified Dashboard

**Goal**: The flock's health story is complete — egg production is tracked against a breed/age/daylight model, feed consumption is derived from load cell data, and production drops trigger alerts. A single overview screen surfaces all garden zones and the flock summary together.

**Depends on**: Phase 2

**Requirements**: FLOCK-01, FLOCK-02, FLOCK-03, FLOCK-04, FLOCK-05, FLOCK-06, UI-01

**Success Criteria** (what must be TRUE):
  1. A farmer can enter the day's egg count from the dashboard; the entry is stored and the 30-day production trend chart updates immediately showing actual vs. expected production
  2. The expected production model calculates daily expected egg count from flock size, breed lay rate, age factor, and daylight hours; the model values are visible and configurable via flock configuration
  3. When the 3-day rolling average of egg production falls below 75% of expected, a production drop alert appears in the persistent alert bar
  4. Feed consumption rate is derived from daily load cell weight delta and displayed on the dashboard; sudden drops in consumption are visible as a trend signal
  5. The overview screen shows all garden zones (composite health score, current moisture) and flock summary (door status, egg count today, production trend indicator) on one screen without scrolling on a tablet

**Plans**: 6 plans

Plans:
- [x] 03-01-PLAN.md — Backend core: flock config store, egg estimator, production model, feed consumption, alert extensions, bridge integration
- [x] 03-02-PLAN.md — Frontend: TypeScript types, WS store extensions, TabBar 4-tab update, route restructure, Home tab, FlockSummaryCard, ZoneCard compact
- [x] 03-03-PLAN.md — CoopPanel extensions: egg count section, HenPresentIndicator, ProductionChart (uPlot), FeedSparkline (inline SVG), refresh button
- [x] 03-04-PLAN.md — FlockSettings form at /coop/settings: breed, hatch date, flock size, lighting, tare weight, hen threshold, egg weight
- [ ] 03-05-PLAN.md — Human verification checkpoint: Home tab, Coop tab, flock settings, alerts, mobile layout
- [x] 03-06-PLAN.md — Flock REST API router (config CRUD, egg-history, refresh-eggs) and WebSocket snapshot extensions

**UI hint**: yes

---

### Phase 4: ONNX AI Layer and Recommendation Engine

**Goal**: ML-backed ONNX models replace the rule-based recommendation engine for zone health scoring, irrigation schedule optimization, and flock production anomaly detection — behind the exact same recommend-and-confirm UX delivered in Phase 2. A model maturity indicator manages farmer expectations during the cold-start period.

**Depends on**: Phase 2 (recommend-and-confirm UX), Phase 3 (flock data model)

**DATA MATURITY GATE**: Phase 4 work cannot begin until at least 4 weeks of GOOD-quality-flagged sensor data exists in TimescaleDB from Phase 1. Check the quality flag distribution before starting. If the ratio of GOOD-flagged readings is below 80% for any zone, investigate sensor calibration before training. AI-06 (training only on GOOD-flagged data) is non-negotiable.

**AI stack confirmation**: ONNX Runtime is the primary inference engine. Ollama/LLMs are explicitly wrong for sensor classification and anomaly detection — they are too slow, too memory-hungry, and produce unstructured output that must be re-parsed. If natural-language recommendation summaries are desired later, Ollama is optional and must be confirmed to fit in hub RAM headroom after all other services are running.

**Requirements**: AI-03, AI-06, AI-07

**Success Criteria** (what must be TRUE):
  1. ONNX Runtime models generate irrigation recommendations, zone health scores, and flock anomaly signals; recommendations appear in the existing recommendation queue with the same approve/reject UX as Phase 2 rule-based recommendations
  2. The inference service uses only GOOD-quality-flagged sensor data as model inputs; SUSPECT and BAD readings are excluded from both training datasets and live inference feature windows
  3. Scheduled inference runs automatically: zone health every 15 minutes, irrigation every 1 hour, flock health every 30 minutes; a threshold crossing in any zone triggers immediate re-inference for that zone
  4. The model maturity indicator in the UI shows recommendation count and approval/rejection rate per recommendation type; during cold start it displays a clear message that the model is still learning

**Plans**: 5 plans

Plans:
- [x] 04-01-PLAN.md — Data foundation: feature aggregator with GOOD-flag filter, maturity tracker, synthetic data generator CLI, new package dependencies
- [x] 04-02-PLAN.md — ONNX inference service with hot-reload, three training pipelines (zone health, irrigation, flock anomaly) with regression protection
- [x] 04-03-PLAN.md — Bridge integration: APScheduler inference scheduler, model watcher, AI/Rules toggle persistence, API settings endpoints
- [x] 04-04-PLAN.md — Dashboard UI: AIStatusCard, DomainMaturityRow, AISettingsToggle, settings route, RecommendationCard source badge, header settings icon
- [x] 04-05-PLAN.md — Human verification checkpoint: full Phase 4 end-to-end integration test

**UI hint**: yes

---

### Phase 5: Operational Hardening

**Goal**: The system survives daily use over months — pH sensors are calibrated on schedule, sensor calibration offsets are managed from the hub, push notifications reach the farmer's phone via self-hosted ntfy, and data retention policies prevent unbounded storage growth.

**Depends on**: Phase 2 (alert infrastructure), Phase 3 (flock data)

**Requirements**: ZONE-07, NOTF-03

**Success Criteria** (what must be TRUE):
  1. The dashboard shows a pH calibration due-date reminder when any pH sensor's last calibration date is older than 2 weeks; the farmer can record a new calibration and the updated offset is applied to subsequent readings at ingestion
  2. Self-hosted ntfy integration (if configured) delivers push notifications to iOS and Android for the same events that trigger in-app alerts; in-app alerts remain the baseline and ntfy is additive
  3. Raw sensor data older than 90 days is automatically purged; hourly rollup aggregates are retained for 2 years; the dashboard reflects actual storage usage

**Plans**: 4 plans

Plans:
- [x] 05-01-PLAN.md — pH calibration backend: DB migration, CalibrationStore extension, AlertEngine overdue alert, periodic check loop, calibration API router
- [x] 05-02-PLAN.md — ntfy push notification backend: NtfySettings sidecar, ntfy dispatch, bridge integration, ntfy/storage API routers, data retention DDL
- [x] 05-03-PLAN.md — All frontend: calibration settings page, ntfy settings page, storage settings page, zone detail inline action, settings navigation
- [x] 05-04-PLAN.md — Human verification checkpoint: full Phase 5 end-to-end feature verification

**UI hint**: yes

---

### Phase 6: Hardware Shopping List and Wiring Diagrams

**Goal**: A farmer with zero electronics experience can purchase every component and wire the complete system by following the documentation alone. Every connection (GPIO, I2C, relay, solenoid, limit switch, load cell, power supply) is documented with pin numbers, wire colors, and physical diagrams. The shopping list is organized by subsystem with exact part numbers, quantities, and sourcing links.

**Depends on**: Phase 5 (all hardware requirements finalized — no more components being added)

**Requirements**: DOC-01, DOC-02

**Success Criteria** (what must be TRUE):
  1. A single shopping list document covers every component in the system organized by subsystem (hub, garden edge nodes, coop edge node, irrigation, power) with exact part numbers/SKUs, quantities, unit prices, and purchase links; a "total cost" summary is included
  2. Wiring diagrams exist for every hardware connection in the system: GPIO pin assignments, I2C bus addresses, relay wiring (NC/NO/COM), solenoid valve wiring, limit switch wiring, load cell wiring, power supply distribution; diagrams use standard notation and are readable by a non-engineer
  3. Each diagram includes a "smoke test" procedure — a simple verification step the farmer can perform after wiring each subsystem to confirm it works before moving on
  4. The documentation cross-references the codebase: each hardware connection maps to the specific config file, GPIO constant, or I2C address used in the software

**Plans**: 5 plans

Plans:
- [ ] 06-01-PLAN.md — Master BOM (docs/hardware/bom.md) with all components, prices, purchase links, total cost summary (~$742), and budget alternatives
- [ ] 06-02-PLAN.md — docs/hardware/ directory scaffold, README navigation index, Fritzing workflow, placeholder diagrams
- [ ] 06-03-PLAN.md — Hub assembly guide (docs/hardware/hub.md) and power distribution guide (docs/hardware/power.md)
- [ ] 06-04-PLAN.md — Garden zone node wiring (docs/hardware/garden-node.md) and irrigation relay/solenoid guide (docs/hardware/irrigation.md)
- [ ] 06-05-PLAN.md — Coop edge node wiring (docs/hardware/coop-node.md) — actuator, limit switches, load cells, sensors

---

### Phase 7: Interactive Tutorial and User Documentation

**Goal**: A new user can set up, configure, and operate the complete platform by following the documentation and interactive tutorial. The tutorial walks through first boot, zone configuration, sensor verification, irrigation setup, coop automation, and daily operation. Full reference documentation covers every feature, configuration option, and troubleshooting scenario.

**Depends on**: Phase 5 (all features complete), Phase 6 (hardware docs complete)

**Requirements**: DOC-03, DOC-04, DOC-05

**Success Criteria** (what must be TRUE):
  1. An interactive tutorial embedded in the dashboard guides a new user through: first boot setup, adding a zone, verifying sensor data, running a manual irrigation, setting up coop automation, and approving a recommendation — each step validates completion before advancing
  2. Full reference documentation covers every dashboard screen, every configuration option, every alert type, and every automation rule with screenshots and examples
  3. A troubleshooting guide covers the 20 most common failure modes (sensor offline, stale data, stuck sensor, failed irrigation, stuck door, MQTT disconnection, etc.) with diagnostic steps and resolution
  4. Documentation is versioned alongside the codebase and builds automatically (no separate publishing step)

**Plans**: TBD

**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Hardware Foundation and Sensor Pipeline | 8/8 | Complete | - |
| 2. Actuator Control, Alerts, and Dashboard V1 | 6/7 | Gap closure in progress | 2026-04-10 |
| 3. Flock Management and Unified Dashboard | 5/6 | Complete    | 2026-04-15 |
| 4. ONNX AI Layer and Recommendation Engine | 4/5 | In Progress|  |
| 5. Operational Hardening | 0/4 | Planned | - |
| 6. Hardware Shopping List and Wiring Diagrams | 0/5 | Planned | - |
| 7. Interactive Tutorial and User Documentation | 0/0 | Not started | - |

---

## Coverage

**v1 requirements: 57 total, 57 mapped, 0 orphaned.**

| Phase | Requirements |
|-------|-------------|
| Phase 1 | INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, INFRA-09, ZONE-01, ZONE-02, ZONE-03, ZONE-04, IRRIG-03, COOP-04, UI-04, UI-07 |
| Phase 2 | ZONE-05, ZONE-06, IRRIG-01, IRRIG-02, IRRIG-04, IRRIG-05, IRRIG-06, COOP-01, COOP-02, COOP-03, COOP-05, COOP-06, COOP-07, AI-01, AI-02, AI-04, AI-05, UI-02, UI-03, UI-05, UI-06, NOTF-01, NOTF-02 |
| Phase 3 | FLOCK-01, FLOCK-02, FLOCK-03, FLOCK-04, FLOCK-05, FLOCK-06, UI-01 |
| Phase 4 | AI-03, AI-06, AI-07 |
| Phase 5 | ZONE-07, NOTF-03 |
| Phase 6 | DOC-01, DOC-02 |
| Phase 7 | DOC-03, DOC-04, DOC-05 |

---

*Roadmap created: 2026-04-01*
*Granularity: standard*
