# Backyard Farm Platform

## What This Is

A self-hosted, local-only platform for managing a medium-scale backyard farm — multiple garden zones and a chicken flock. Distributed Raspberry Pi edge nodes collect sensor data, a central Pi 5 hub runs ONNX ML inference and serves the dashboard, and the farmer monitors everything from a single PWA. Push notifications via self-hosted ntfy, pH calibration tracking, and automated data retention round out the operational layer. Complete hardware documentation with shopping list, wiring diagrams, and an interactive tutorial make the system buildable by anyone.

## Core Value

A single dashboard where you can see every zone's sensor readings, irrigation status, and flock health at a glance — and act on ML recommendations without leaving it.

## Requirements

### Validated

**Platform & Infrastructure** — v1.0
- Distributed edge node architecture — Pi Zero 2W per garden zone, Pi 5 for coop and hub
- Central hub aggregates data from all edge nodes via MQTT and serves the UI
- All data and ML inference stays on-premises — no cloud dependency
- Hardware-agnostic sensor layer with pluggable adapters and per-sensor calibration offsets
- HTTPS dashboard accessible on LAN via Caddy reverse proxy
- PWA installable from mobile browser

**Garden & Irrigation** — v1.0
- Soil sensor support per zone: moisture, pH, temperature with quality flags
- Sensor-feedback irrigation triggered by threshold recommendations (farmer approves)
- ML recommends irrigation based on ONNX gradient boosting models (or falls back to rules)
- Per-zone composite health score derived from sensor readings (green/yellow/red)
- pH calibration tracking with overdue alerts and one-tap recording

**Chicken Flock** — v1.0
- Automated coop door — opens at sunrise, closes at sunset via astral calculations
- Feed and water level monitoring with P1 alerts when low
- Daily egg production estimated from nesting box weight sensor
- Flock health alerts — production drops and feed consumption anomalies
- Flock configuration: breed, hatch date, flock size, lighting schedule

**AI & Recommendations** — v1.0
- ONNX Runtime inference for zone health, irrigation, and flock anomaly (3 domains)
- Recommendation engine with recommend-and-confirm UX — farmer approves before execution
- ML/Rules toggle per domain from settings page
- Weekly automatic retraining from GOOD-flagged data with regression check

**Dashboard & UI** — v1.0
- Web dashboard with real-time WebSocket updates
- Unified home screen: zone health cards + flock summary + ML model status
- Persistent P0/P1 alert bar with tap-to-navigate deep links
- Push notifications via self-hosted ntfy (optional, additive to in-app alerts)
- Interactive 8-step onboarding tutorial with localStorage progress

**Documentation** — v1.0
- Complete hardware BOM with exact parts, prices, and fallback specs (~$742)
- Wiring diagrams (Fritzing) for every hardware connection with smoke tests
- Full reference documentation (MkDocs) covering every screen, config, alert, and automation rule
- 20-failure-mode troubleshooting guide (symptom-first)

### Active

(None — all v1.0 requirements validated. Next milestone will define new requirements.)

### Out of Scope

- Cloud sync or remote access outside home network — local-only is a hard constraint
- Computer vision / camera-based plant health — sensor-based approach chosen; cameras deferred
- Fully autonomous execution without approval — recommend-and-confirm is intentional for v1
- Commercial-scale features (fleet management, market pricing, yield analytics) — hobby/medium backyard focus
- Nutrient level sensors — deferred, not available in affordable sensor range for v1

## Context

- **Hardware decided**: Pi Zero 2W (garden zones), Pi 5 4GB (coop), Pi 5 8GB (hub)
- **Sensors decided**: STEMMA Soil (moisture, I2C 0x36), ADS1115 + SEN0161-V2 (pH), DS18B20 (temperature), HX711 (load cells)
- **ML approach**: ONNX Runtime with scikit-learn gradient boosting classifiers — not LLMs
- **Budget**: ~$742 total for complete system (4 zones + coop + hub)
- **144 Python tests, 94 Svelte component tests**, TypeScript build clean
- **MkDocs reference docs** auto-build via `make docs`

## Constraints

- **Connectivity**: Local-only — no cloud APIs, no external inference endpoints
- **Hardware**: Raspberry Pi ecosystem (Zero 2W, Pi 5) — decided in v1.0
- **Scale**: Medium backyard — 4 garden zones, 10-25 chickens; not commercial
- **Autonomy**: Recommend-and-confirm for all actions — no fully autonomous execution

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local-only (no cloud) | Privacy, offline reliability, no recurring costs | Validated v1.0 |
| Distributed edge nodes per zone | Reduces SPOF, nodes closer to sensors/actuators | Validated v1.0 |
| Recommend-and-confirm (not full autonomy) | Farmer stays in control; autonomy can be tuned later | Validated v1.0 |
| Sensor-based plant health (not camera) | Simpler hardware, more actionable data | Validated v1.0 |
| ONNX Runtime (not LLMs) | Classical ML on structured sensor data; runs on Pi hardware | Validated v1.0 |
| Pi Zero 2W for garden nodes | Full Linux, runs Python, WiFi, $15 — simplifies edge software | Validated v1.0 |
| Pi 5 for hub and coop | Docker Compose stack needs 8GB RAM; coop needs GPIO headroom | Validated v1.0 |
| MkDocs for reference docs | Markdown-native, auto-builds, versioned alongside code | Validated v1.0 |
| Fritzing for wiring diagrams | Breadboard-style visuals readable by non-engineers | Validated v1.0 |
| ntfy for push notifications | Self-hosted, no cloud dependency, fire-and-forget via HTTP POST | Validated v1.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-20 after v1.0 milestone completion*
