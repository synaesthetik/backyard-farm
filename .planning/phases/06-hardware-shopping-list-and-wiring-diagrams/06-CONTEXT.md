# Phase 6: Hardware Shopping List and Wiring Diagrams - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete BOM and wiring documentation so a farmer with zero electronics experience can purchase every component and wire the complete system by following the documentation alone. Every connection is documented with pin numbers, wire colors, and physical diagrams. Shopping list organized by subsystem with exact part numbers, quantities, and sourcing links. Each subsystem has a smoke test procedure.

This phase produces documentation only — no application code changes.

</domain>

<decisions>
## Implementation Decisions

### Hardware platform selection
- **D-01:** Garden zone edge nodes: Raspberry Pi Zero 2W (full Linux, runs Python, built-in WiFi, ~$15)
- **D-02:** Coop edge node: Raspberry Pi 4 or 5 (more GPIO, runs ONNX inference, handles motor control + limit switches + load cell + multiple sensors)
- **D-03:** Hub: Raspberry Pi 4 or 5 with 8GB RAM (runs Docker Compose stack: TimescaleDB, bridge, API, dashboard, Caddy)
- **D-04:** Budget target: under $500 total for the complete system (hub + 4 garden nodes + 1 coop node + all sensors, actuators, wiring, enclosures)

### Diagram format and tooling
- **D-05:** Fritzing breadboard-style diagrams for all wiring. Non-engineers understand these instantly.
- **D-06:** Source `.fzz` files committed to the repo under `docs/hardware/fritzing/`
- **D-07:** Rendered PNG images embedded in the Markdown docs for easy viewing on GitHub

### Document structure and hosting
- **D-08:** All hardware docs live in `docs/hardware/` in the repo (Markdown + images)
- **D-09:** Organized by physical location (matches build order):
  - `docs/hardware/bom.md` — Master shopping list with all components, quantities, prices, links
  - `docs/hardware/hub.md` — Hub assembly and wiring
  - `docs/hardware/garden-node.md` — Garden zone edge node (template for all 4 zones)
  - `docs/hardware/coop-node.md` — Coop edge node (motor, limit switches, load cell, sensors)
  - `docs/hardware/irrigation.md` — Solenoid valves, relay wiring, water supply
  - `docs/hardware/power.md` — Power supply distribution, voltage regulators, protection

### Sourcing philosophy
- **D-10:** Each component gets an exact primary recommendation with purchase link (Amazon, Adafruit, SparkFun, or equivalent)
- **D-11:** Each component also gets a generic fallback spec description ("look for: capacitive soil moisture sensor, 3.3V, I2C compatible") for when the primary is out of stock
- **D-12:** Include a "total cost" summary in bom.md with estimated total and per-subsystem breakdown

### Claude's Discretion
- Specific sensor module choices (researcher should recommend best value-for-money options)
- Exact GPIO pin assignments (planner can optimize for physical layout)
- Wire color conventions (follow standard practices)
- Enclosure/weatherproofing recommendations
- Smoke test procedure specifics for each subsystem

</decisions>

<specifics>
## Specific Ideas

- Documentation should be followable by someone who has never touched a breadboard — assume zero electronics experience
- Each subsystem doc should follow the same structure: parts needed (links back to BOM), wiring diagram, pin mapping table, smoke test procedure, common mistakes
- Cross-reference the codebase: each hardware connection maps to the specific config file, GPIO constant, MQTT topic, or I2C address used in the software
- The BOM should be organized so you can buy everything in one shopping trip / one online order

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above and in these project files:

### Project requirements
- `.planning/REQUIREMENTS.md` §DOC-01, §DOC-02 — Hardware documentation requirements
- `.planning/ROADMAP.md` §Phase 6 — Success criteria and dependency on Phase 5

### Software cross-references (for hardware-to-code mapping)
- `hub/bridge/main.py` — MQTT topics, sensor types, actuator control
- `hub/bridge/calibration.py` — Calibration offset handling (maps to pH sensor hardware)
- `hub/bridge/alert_engine.py` — Alert definitions that correspond to hardware sensors
- `hub/init-db.sql` — Database schema showing sensor_type values and zone_id patterns
- `config/hub.env` — Environment variables for MQTT, DB, and port configuration

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No edge node code exists in the repo yet — this is hub-only software currently
- The bridge expects MQTT messages with specific topic patterns and JSON payloads
- Sensor types are: moisture, ph, temperature (garden), plus load_cell, limit_switch (coop)

### Established Patterns
- MQTT topics follow: `farm/{zone_id}/{sensor_type}` pattern
- Edge nodes authenticate to MQTT via `mosquitto/passwd` credentials
- Config is in `config/hub.env` with env vars for host IPs, ports, passwords

### Integration Points
- Edge node code would connect via MQTT to the hub's Mosquitto broker
- Each zone edge node publishes sensor readings; hub bridge subscribes and processes
- Coop edge node additionally controls actuators (door motor, irrigation relays)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-hardware-shopping-list-and-wiring-diagrams*
*Context gathered: 2026-04-17*
