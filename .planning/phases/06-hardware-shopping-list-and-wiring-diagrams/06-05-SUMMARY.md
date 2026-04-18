---
phase: 06-hardware-shopping-list-and-wiring-diagrams
plan: "05"
subsystem: hardware-documentation
tags: [hardware, coop-node, wiring, L298N, HX711, limit-switches, documentation]

dependency_graph:
  requires:
    - "06-01"  # bom.md completed
    - "06-02"  # hub.md completed
  provides:
    - docs/hardware/coop-node.md
  affects:
    - edge/daemon/sensors.py  # GPIO constants documented for HX711, float switch
    - edge/daemon/rules.py    # COOP_HARD_CLOSE GPIO wiring documented
    - edge/daemon/main.py     # limit switch GPIO constants documented

tech_stack:
  added: []
  patterns:
    - "Standard 8-section hardware doc template (Parts, Diagram, Wiring, GPIO, Cross-Ref, Smoke Test, Common Mistakes)"
    - "L298N H-bridge motor control with direction truth table"
    - "HX711 GPIO bit-bang protocol (not I2C/SPI)"
    - "Roller limit switch pull-down configuration"

key_files:
  created:
    - docs/hardware/coop-node.md
  modified: []

decisions:
  - "Used subsection headers A–F within Wiring Tables to group by subsystem (actuator, limit switches, HX711 ×2, float switch, DS18B20, relay) — matches plan specification"
  - "Common GND note placed as first Common Mistake — most safety-critical wiring error for L298N/Pi combination"
  - "Config File Cross-Reference table has 17 rows linking every GPIO constant to its source file (sensors.py, rules.py, main.py, coop_scheduler.py, mqtt-topic-schema.md)"

metrics:
  duration_minutes: 8
  completed_date: "2026-04-16"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 06 Plan 05: Coop Node Wiring Guide Summary

## One-liner

Complete coop edge node wiring guide covering L298N actuator control, roller limit switches (GPIO bit-bang), dual HX711 load cells, float switch, DS18B20 temperature, and 4-channel relay expansion board on Raspberry Pi 5.

## What Was Built

`docs/hardware/coop-node.md` — the most complex subsystem document in the hardware documentation set. Covers all six hardware subsystems on the coop Pi 5 node.

### Document Sections

1. **Parts Needed** — Links to all 10 components in BOM Section 3 with quantities
2. **Overview Diagram** — Fritzing diagram reference (coop-node.fzz/png) with dual power rail explanation
3. **Wiring Tables** — Six subsections (A–F):
   - A: L298N H-bridge (3 GPIO direction/enable pins + 12V motor power)
   - B: Limit switches (GPIO5, GPIO6, pull-down wiring + Python snippet)
   - C: HX711 load cells (GPIO bit-bang — feed hopper GPIO23/24, nesting box GPIO25/8)
   - D: Water level float switch (GPIO16, pull-down)
   - E: DS18B20 temperature sensor (GPIO4, 1-Wire, 4.7kΩ pull-up)
   - F: 4-channel relay board (GPIO12/13/19/26, expansion pre-wired)
4. **GPIO Pin Assignment Table** — 18 rows covering all coop node connections
5. **Config File Cross-Reference** — 17 rows linking to sensors.py, rules.py, main.py, coop_scheduler.py, and mqtt-topic-schema.md
6. **Smoke Test** — 8 steps: Pi boot → L298N polarity test (multimeter) → actuator movement → limit switch GPIO read → HX711 weight test → float switch test → DS18B20 sysfs read → MQTT topic verification
7. **Common Mistakes** — 6 bullets including critical common GND safety note, end-stop protection, load cell wire color variation, HX711 taring, SCK/DOUT swap diagnosis, and limit switch mounting

## Deviations from Plan

None — plan executed exactly as written. Document content was specified verbatim in the plan's `<action>` block and reproduced faithfully with no modifications.

## Known Stubs

None. This is documentation only — no code stubs. The Config File Cross-Reference table explicitly notes which GPIO constants need to be updated from Phase 1 stubs in edge/daemon/sensors.py, rules.py, and main.py — but those are in future code, not in this document.

## Threat Flags

No new security-relevant surface introduced. This is documentation only. All threat mitigations from the plan's threat model are present:
- T-06-11: Common GND missing → documented as Common Mistake #1 with explicit warning
- T-06-12: Actuator end-stop damage → documented in Common Mistake #2 and Smoke Test Step 3
- T-06-13: HX711 wire color variation → documented in wiring table note and Common Mistake #3
- T-06-14: lat/long disclosure → accepted; documented as "update to your location"

## Self-Check: PASSED

- [x] `docs/hardware/coop-node.md` exists
- [x] grep "L298N" returns 23 matches (≥5 required)
- [x] grep "GPIO5|GPIO6" returns 9 matches (≥3 required)
- [x] grep "HX711" returns 36 matches (≥5 required)
- [x] grep "COOP_HARD_CLOSE" returns 1 match
- [x] grep "Smoke Test" returns match
- [x] grep "Common Mistakes" returns match
- [x] grep "common GND|common ground" returns 2 matches
- [x] Commit 69389a0 exists

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write docs/hardware/coop-node.md | 69389a0 | docs/hardware/coop-node.md (created, 370 lines) |
