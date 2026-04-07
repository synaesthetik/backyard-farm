# Phase 1: Hardware Foundation and Sensor Pipeline - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Trustworthy sensor data flows from every edge node to the hub with quality flags, node health is visible on a minimal dashboard, and all hardware failsafes are confirmed before any actuator is connected.

This phase delivers:
- Hub service stack (Docker Compose: Mosquitto, TimescaleDB, FastAPI, Caddy)
- MQTT topic schema and per-node ACL credentials
- Edge node sensor daemon (polling loop, local SQLite buffer, reconnect with replay)
- Edge node local rule engine (emergency irrigation shutoff + coop door hard-close, no hub required)
- Hub MQTT bridge (quality flags + calibration offsets applied at ingestion, TimescaleDB write)
- Heartbeat monitoring, stuck-reading detection, minimal dashboard (zone cards + system health panel)

Phase 1 does NOT deliver: alert bar, manual irrigation control, coop door scheduling, recommendation queue, PWA service worker. Those are Phase 2 scope.

</domain>

<decisions>
## Implementation Decisions

### Sensor Hardware — Edge Node

- **D-01:** **Soil moisture sensor: TBD — research spike required in plan 01-03.** The researcher/planner must include a task to evaluate and document the chosen moisture sensor module (capacitive I2C vs ADS1115 ADC) before writing the sensor daemon driver. Moisture model selection drives whether an I2C multiplexer (TCA9548A) is needed on each zone node.
- **D-02:** **pH sensor: Analog pH probe + ADS1115 ADC over I2C.** Standard gravity-style pH electrode connected to an ADS1115 16-bit ADC. Calibration via pH 4.0 and 7.0 buffer solutions; calibration offset stored per-sensor on the hub and applied at ingestion (ZONE-03). The ADS1115 is already on the I2C bus for pH — the moisture driver must be compatible with this bus if moisture is also I2C.
- **D-03:** **Temperature sensor: DS18B20 waterproof probe on 1-wire bus.** Use the `w1-therm` Linux kernel module on Raspberry Pi. Multiple DS18B20 sensors can share one GPIO pin. No ADC required.
- **D-04:** **Edge node hardware: Raspberry Pi Zero 2W.** One Pi Zero 2W per garden zone node. 512MB RAM, quad-core ARM64, built-in Wi-Fi. Driver code must target 64-bit Raspberry Pi OS Lite (no desktop). GPIO and 1-wire (DS18B20) must work on Pi Zero 2W GPIO header — confirm pin mapping in research spike.
- **D-05:** **I2C multiplexer decision deferred to moisture sensor research spike.** If the selected moisture sensor and pH ADS1115 share I2C addresses that conflict, a TCA9548A multiplexer must be added. The research spike (D-01) resolves this.

### Hub Hardware

- **D-06:** **Hub: Raspberry Pi 5 8GB.** Docker Compose targets ARM64 (linux/arm64) base images for all services. TimescaleDB, Mosquitto, FastAPI, and Caddy must all have ARM64 Docker images available — confirm in plan 01-01.
- **D-07:** **Hub storage: SSD via USB3 or NVMe HAT.** Docker Compose volumes for TimescaleDB data must point to the SSD mount path (not the SD card). Plan 01-01 must include a task to verify the SSD is mounted, configure the Docker volume bind-mount to the SSD path, and document the expected path (e.g., `/mnt/ssd/data`).
- **D-08:** **Static IP and NTP setup: included in plan 01-01.** Hub does not yet have a static IP assigned. Plan 01-01 must include:
  - Configure DHCP reservation on router (or static IP in `/etc/dhcpcd.conf` / `nmconnection`) for the hub's MAC address
  - Install and configure `chrony` as NTP server for the LAN (edge nodes will sync to hub)
  - Document the assigned IP in a `config/hub.env` file that Caddy and other services reference

### MQTT and Broker

- **D-09 (from roadmap/requirements):** MQTT QoS 1 for all sensor publishes. Per-node ACL credentials defined before any node software is written (INFRA-08). Topic schema and ACL design is plan 01-02 and must be completed and documented before plan 01-03 (edge daemon) begins.

### Quality Flag Logic

- **D-10:** **Flag method: range-based per sensor type.** Applied at ingestion in the hub MQTT bridge (plan 01-05). No history required — range check is stateless and applies from the first reading.
- **D-11:** **Default sensor plausible ranges (configurable as env vars in the bridge service):**

  | Sensor | BAD condition | SUSPECT condition | GOOD condition |
  |--------|--------------|------------------|----------------|
  | Soil moisture | VWC < 0% or > 100% | VWC < 2% or > 98% | 2% ≤ VWC ≤ 98% |
  | pH | pH < 0 or > 14 | pH < 3 or > 10 | 3 ≤ pH ≤ 10 |
  | Temperature | °C < -10 or > 80 | °C < 0 or > 60 | 0°C ≤ temp ≤ 60°C |

  Named constants in bridge code (e.g., `MOISTURE_BAD_MIN`, `MOISTURE_SUSPECT_MIN`). Override via env vars in `docker-compose.yml`.

- **D-12:** **Stuck-reading detection is a separate display state — does NOT downgrade the quality flag.** A reading flagged GOOD that has been identical for 30+ consecutive readings is GOOD + STUCK. The dashboard shows both the quality badge and the stuck indicator (per UI-SPEC). This keeps GOOD-flagged data usable for Phase 4 model training even when a sensor is in a stable environment. The planner must store a `stuck` boolean column in TimescaleDB alongside the `quality` column.

### Emergency Rule Thresholds — Edge Node Local Rule Engine (Plan 01-04)

- **D-13:** **Emergency irrigation shutoff: trigger at ≥ 95% VWC.** The edge node rule engine forces the local relay closed (irrigation valve off) when soil moisture reads ≥ 95% VWC. This rule executes without hub involvement — it is a local safety backstop. Threshold stored as `EMERGENCY_MOISTURE_SHUTOFF_VWC` env var (default: 95) in the edge node environment file.
- **D-14:** **Coop door hard-close: time limit only.** The coop node rule engine forces the door closed if it is open at or after the hard-close time, regardless of hub connection or schedule state. No hub-silence trigger in Phase 1. Hard-close time stored as `COOP_HARD_CLOSE_HOUR` env var (default: 21, meaning 21:00 local time). The edge node must read system time — hub NTP sync (D-08) ensures clock accuracy across nodes.

### Dashboard UI

- **D-15 (from UI-SPEC):** Dashboard fully specified in `01-UI-SPEC.md`. SvelteKit + Svelte 5 runes. Dark theme. Four component types: ZoneCard, SensorValue, NodeHealthRow, SystemHealthPanel. Exact colors, typography, spacing, copywriting, and accessibility requirements are locked. No component library — hand-authored Svelte 5 components only. Lucide icons, Inter font.
- **D-16 (from UI-SPEC):** Real-time updates via WebSocket to `/ws/dashboard`. Server sends full state snapshot on connect, then deltas. Stale logic runs client-side using `received_at` timestamp. Do not clear values on disconnect.

### Claude's Discretion

- SQLite schema for edge node local buffer (column names, index strategy)
- TimescaleDB hypertable schema (column names beyond the required: `zone_id`, `sensor_type`, `value`, `quality`, `stuck`, `received_at`, `calibration_applied`)
- MQTT topic schema design (within the documented structure from plan 01-02)
- Reconnect backoff strategy for edge node MQTT client
- FastAPI endpoint design for the WebSocket `/ws/dashboard` and any REST endpoints needed for zone config
- Python vs other language for hub MQTT bridge (Python with paho-mqtt is the natural choice given FastAPI)
- Mosquitto configuration details (persistence, logging levels, listener ports)
- Caddy configuration for local HTTPS (self-signed vs mkcert vs local CA)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 Core
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, 6 pre-defined plan slugs (01-01 through 01-06), hardware procurement checklist, hardware failsafe requirements
- `.planning/REQUIREMENTS.md` — Full requirement text for INFRA-01 through INFRA-09, ZONE-01 through ZONE-04, IRRIG-03, COOP-04, UI-04, UI-07

### UI Contract
- `.planning/phases/01-hardware-foundation-and-sensor-pipeline/01-UI-SPEC.md` — Approved UI design contract: component inventory, spacing scale, color palette, typography, page layout, state definitions, real-time behavior contract, PWA minimum requirements, copywriting contract, accessibility minimums

### Project Context
- `.planning/STATE.md` — Current blockers (sensor model selection, relay boot-state), accumulated decisions, phase progress

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — this is Phase 1, greenfield project. No existing codebase to reuse from.

### Established Patterns
- None yet — Phase 1 establishes the patterns that later phases will follow.

### Integration Points
- Hub FastAPI service is the integration point for all downstream phases. The WebSocket endpoint and TimescaleDB schema established in Phase 1 must be designed with Phase 2 (actuator commands, alert system) in mind.

</code_context>

<specifics>
## Specific Ideas

- Pi Zero 2W nodes: confirm all required kernel modules (w1-therm for DS18B20, i2c-dev for ADS1115) are available on 64-bit Raspberry Pi OS Lite before writing daemon code. Include a hardware validation checklist task in plan 01-03.
- ADS1115: I2C address is 0x48 by default (ADDR pin to GND). If moisture sensor also uses ADS1115 or shares 0x48, either the ADDR pin must be changed on one device or a TCA9548A multiplexer is needed. Research spike resolves this.
- TimescaleDB on ARM64: confirm the TimescaleDB Docker image supports linux/arm64 — as of 2024 it does, but the research spike should verify the current tag.
- Caddy for local HTTPS: mkcert or a local CA approach gives a stable cert that browsers trust on the LAN without repeated warnings (per success criterion 5). Plan 01-01 should document the chosen approach.
- NTP: `chrony` is preferred over `ntpd` on modern Raspberry Pi OS. Configure hub as stratum 2 server for LAN.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 1 scope.

</deferred>

---

*Phase: 01-hardware-foundation-and-sensor-pipeline*
*Context gathered: 2026-04-07*
