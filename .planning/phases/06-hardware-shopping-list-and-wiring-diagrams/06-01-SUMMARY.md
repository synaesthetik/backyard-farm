---
phase: 06-hardware-shopping-list-and-wiring-diagrams
plan: "01"
subsystem: hardware-documentation
tags: [bom, hardware, shopping-list, documentation, DOC-01]
dependency_graph:
  requires: []
  provides: [docs/hardware/bom.md]
  affects: [docs/hardware/hub.md, docs/hardware/garden-node.md, docs/hardware/coop-node.md, docs/hardware/irrigation.md, docs/hardware/power.md]
tech_stack:
  added: []
  patterns: [markdown-bom-tables, subsystem-organized-procurement, primary-plus-fallback-spec]
key_files:
  created:
    - docs/hardware/bom.md
  modified: []
decisions:
  - "Pi 5 4GB selected for coop node (over Pi 4B) — same price tier after 2026 RAM hikes, better ONNX performance"
  - "Adafruit STEMMA Soil Sensor (ID 4026) chosen for garden zone moisture — 4 selectable I2C addresses eliminates need for TCA9548A multiplexer"
  - "Budget honest: $742 estimated total flagged explicitly vs $500 target with 5 alternatives"
  - "Wire color convention: red=3.3V/5V, orange=12V, black=GND, blue=SDA, yellow=SCL, green=GPIO, white=1-Wire, gray=COM, purple=NC"
metrics:
  duration_seconds: 136
  completed_date: "2026-04-18"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 6 Plan 01: Master Bill of Materials Summary

**One-liner:** Complete 30-component BOM across 5 subsystems with per-row fallback specs, primary purchase links, $742 realistic total flagged against $500 target, and a wire color convention table for all wiring diagrams.

## What Was Built

`docs/hardware/bom.md` — the master shopping document satisfying DOC-01. A person with zero electronics experience can open this file and purchase every component for the complete backyard farm platform from one document.

Sections:
- **Before You Buy** — framing and reading instructions
- **Budget Summary** — $742 honest total with per-subsystem breakdown and explicit $500 target miss explanation
- **Section 1: Hub** — Pi 5 8GB, M.2 HAT+, NVMe SSD, official PSU (subtotal ~$229)
- **Section 2: Garden Zone Edge Nodes (×4)** — Pi Zero 2W, Samsung Pro Endurance SD, STEMMA soil sensor, ADS1115 ADC, DS18B20 temp probe, pH meter V2, resistors, JST cables (subtotal ~$270)
- **Section 3: Coop Edge Node (×1)** — Pi 5 4GB, ECO-WORTHY linear actuator, L298N H-bridge, HX711 load cells, float switch, limit switches, relay board (subtotal ~$148)
- **Section 4: Irrigation** — 4× US Solid NC solenoid valves with prominent IRRIG-03 safety callout, relay board, Y-splitter, NPT adapters (subtotal ~$74)
- **Section 5: Power, Enclosures, Wiring** — IP65 power supplies, buck converters, project enclosures, cable glands, wire assortments, heat shrink, Wago connectors (subtotal ~$202)
- **Budget Alternatives** — 5 options for reducing cost (staging procurement, AliExpress, Pi 4B coop node, shared PSUs, Pi Zero coop node)
- **Component Quick-Reference Card** — all 31 line items in a single compact table for clipboard ordering
- **Wire Color Convention** — 9-color standard used consistently throughout all wiring diagrams

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: Write bom.md | cd86fa9 | docs(06-01): write master bill of materials for complete system |

## Deviations from Plan

None — plan executed exactly as written.

The plan's interfaces section contained the complete component inventory and structure. The document was written directly from those specifications without ambiguity or gaps.

## Known Stubs

None. All component rows have real part numbers, real prices, real purchase links, and real fallback specs. No placeholder data.

## Threat Flags

None. `docs/hardware/bom.md` is documentation only. All purchase links are to public product pages (Amazon, Adafruit, DFRobot, raspberrypi.com). No credentials, no private data. T-06-01 (Information Disclosure — purchase links) is accepted per the plan's threat model — this is appropriate.

The document does not expose env var names or credential values (T-06-03 disposition: mitigate). Those are handled in the hub assembly doc, not the BOM.

## Self-Check: PASSED

- [x] `docs/hardware/bom.md` exists at correct path
- [x] Commit cd86fa9 verified: `git log --oneline | grep cd86fa9`
- [x] `grep -c "adafruit.com/product/4026" docs/hardware/bom.md` returns 1
- [x] `grep "normally-closed" docs/hardware/bom.md` returns matches (solenoid safety req)
- [x] `grep "B088D7N85K" docs/hardware/bom.md` returns match (linear actuator)
- [x] `grep "~\$742" docs/hardware/bom.md` returns matches (budget total)
- [x] Budget Alternatives section has 5 options
- [x] Wire Color Convention table present
