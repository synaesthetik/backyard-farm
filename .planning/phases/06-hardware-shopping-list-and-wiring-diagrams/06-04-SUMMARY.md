---
phase: 06-hardware-shopping-list-and-wiring-diagrams
plan: "04"
subsystem: hardware-docs
tags: [documentation, hardware, wiring, garden-node, irrigation, sensors]
dependency_graph:
  requires: ["06-01", "06-02"]
  provides: ["docs/hardware/garden-node.md", "docs/hardware/irrigation.md"]
  affects: ["DOC-02"]
tech_stack:
  added: []
  patterns:
    - "8-section hardware subsystem documentation template"
    - "Wire color convention (Red=3.3V, Orange=12V, Black=GND, Blue=SDA, Yellow=SCL, Green=GPIO, White=1-Wire, Purple=NC, Gray=COM)"
key_files:
  created:
    - docs/hardware/garden-node.md
    - docs/hardware/irrigation.md
  modified: []
decisions:
  - "GPIO17 (BCM, Pin 11) assigned as primary irrigation relay control pin (IN1) per planner recommendation"
  - "Active-LOW relay behavior documented as the expected default with mandatory test before wiring"
  - "Double-NC safety approach: NC relay terminal + NC valve both required"
  - "STEMMA solder jumper bridging instructions included for per-zone I2C address assignment"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 06 Plan 04: Garden Node and Irrigation Wiring Guides Summary

**One-liner:** Complete wiring guides for Pi Zero 2W garden zone node (STEMMA 0x36 + ADS1115 pH 0x48 + DS18B20 1-Wire) and irrigation relay board (GPIO17/IN1, active-LOW, NC valve + NC terminal double-safety).

## What Was Built

Two subsystem hardware documentation files following the project's standard 8-section template.

**docs/hardware/garden-node.md** — Complete wiring guide for a single garden zone edge node (Pi Zero 2W). Covers:
- All 3 sensor connections: Adafruit STEMMA Soil Sensor (I2C 0x36), ADS1115 pH ADC (I2C 0x48), DS18B20 temperature probe (1-Wire GPIO4)
- Full wiring table (15 connections), GPIO pin assignment table (7 rows), I2C address summary
- I2C and 1-Wire kernel module enablement commands
- Config File Cross-Reference linking hardware connections to `edge/daemon/sensors.py` class names, MQTT topics, `config/hub.env` variables, and MQTT credentials
- 6-step smoke test from SSH login through TimescaleDB row verification
- Per-Zone I2C Address Configuration table — all 4 zones with STEMMA solder jumper instructions (0x36–0x39)
- 5 common mistakes (4.7kΩ pull-up, extra I2C pull-ups, address conflicts, analog pH direct connection, GPIO power)

**docs/hardware/irrigation.md** — Complete wiring guide for relay board + solenoid valves. Covers:
- Relay board GPIO control wiring (GPIO17/IN1 per zone, 5V VCC)
- Solenoid valve wiring via relay COM/NC terminals to 12V PSU
- Active-HIGH vs active-LOW critical relay test (Python script + checkbox to record result)
- Config File Cross-Reference linking to `edge/daemon/rules.py` execute_action stub and MQTT topics
- 5-step smoke test from power LED through end-to-end MQTT command test
- 5 common mistakes (NO valve, NO terminal, untested relay logic, back-EMF, direct GPIO solenoid)

## Deviations from Plan

None — plan executed exactly as written. Both documents follow the full content specified in the plan's `<action>` sections verbatim, with cross-references verified against actual codebase files (`edge/daemon/sensors.py`, `edge/daemon/rules.py`, `docs/mqtt-topic-schema.md`).

Minor correction: irrigation.md MQTT command topic uses `farm/{zone_id}/commands/irrigate` (matching actual `docs/mqtt-topic-schema.md`) rather than the slightly different `farm/{zone_id}/commands/irrigation` shown in the plan's interfaces section. The schema document is authoritative.

## Known Stubs

**garden-node.md** — The STEMMA soil sensor references `MoisturePlaceholder` in `edge/daemon/sensors.py`. The document includes a note explaining this and providing the correct replacement instructions (`adafruit-circuitpython-seesaw`). The documentation is complete; the code stub is a pre-existing Phase 1 known gap.

**irrigation.md** — The relay GPIO pin and active-level constants reference `edge/daemon/rules.py` `execute_action` as a Phase 1 stub. The document correctly documents this as "stub in Phase 1, wire in Phase 2". The documentation is complete; the code implementation is a future phase deliverable.

## Threat Flags

None — documentation only, no new network endpoints or trust boundaries introduced.

## Self-Check: PASSED

- `docs/hardware/garden-node.md` exists: FOUND
- `docs/hardware/irrigation.md` exists: FOUND
- `grep 0x36 garden-node.md` returns 10 matches (need 3+): PASS
- `grep 0x48 garden-node.md` returns 7 matches (need 2+): PASS
- `grep i2cdetect garden-node.md` returns 2 matches: PASS
- `grep NC irrigation.md` returns 14 matches (need 5+): PASS
- `grep active-LOW irrigation.md` returns 6 matches (need 3+): PASS
- `grep sensors.py garden-node.md` returns 4 matches: PASS
- `grep rules.py irrigation.md` returns 4 matches: PASS
- Commit 4a07f3a (garden-node.md): FOUND
- Commit 678816a (irrigation.md): FOUND
