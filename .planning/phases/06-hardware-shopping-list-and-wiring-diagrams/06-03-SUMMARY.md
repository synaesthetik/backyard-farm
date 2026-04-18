---
phase: 06-hardware-shopping-list-and-wiring-diagrams
plan: "03"
subsystem: hardware-docs
tags: [documentation, hub, power, raspberry-pi, wiring, buck-converter]
requirements: [DOC-02]

dependency_graph:
  requires: [06-01, 06-02]
  provides: [hub-assembly-guide, power-distribution-guide]
  affects: [docs/hardware/hub.md, docs/hardware/power.md]

tech_stack:
  added: []
  patterns:
    - Standard 8-section hardware doc template (Parts Needed, Overview Diagram, Wiring/Assembly, Network/Wiring, Config Cross-Reference, Software Setup, Smoke Test, Common Mistakes)
    - Single 12V cable run strategy using LM2596 buck converter for outdoor nodes
    - Config file cross-reference linking hardware connections to config/hub.env variables

key_files:
  created:
    - docs/hardware/hub.md
    - docs/hardware/power.md
  modified: []

decisions:
  - Hub doc uses "Physical Assembly Table" and "Network Configuration Table" instead of "Wiring Table" and "GPIO Pin Assignment Table" since the hub is a network-only device with no GPIO sensor connections
  - power.md smoke test covers buck converter bench test first (before any load) to prevent Pi damage from incorrect voltage — matches threat model T-06-07 mitigation

metrics:
  duration: "~10 minutes"
  completed: "2026-04-16"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 06 Plan 03: Hub Assembly and Power Distribution Guides Summary

Hub and power subsystem documentation written as complete, self-contained guides — a reader with zero electronics experience can assemble the Pi 5 hub, configure Docker Compose services, and safely set up 12V outdoor power distribution using only these two files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write docs/hardware/hub.md | bfa6c8d | docs/hardware/hub.md (created) |
| 2 | Write docs/hardware/power.md | b42d2e1 | docs/hardware/power.md (created) |

## What Was Built

### docs/hardware/hub.md

Hub assembly guide following the standard 8-section template with adaptations for a network-only device:

- **Parts Needed** — Links to BOM Section 1 for all 4 hub components
- **Overview Diagram** — ASCII network architecture diagram (no GPIO wiring needed)
- **Physical Assembly** — 7-step table covering M.2 HAT+ attachment, NVMe SSD insertion, Ethernet, monitor, PSU
- **Network Configuration** — Table with Ethernet-only requirement, static IP instructions, port assignments
- **Config File Cross-Reference** — Maps hub hardware to all relevant `config/hub.env` variables; MQTT_BRIDGE_PASS documented as generate-passwords.sh output only (T-06-06 mitigation)
- **Software Setup** — 5 numbered sections: OS flash, first boot, NVMe migration, Docker install, Compose startup
- **Smoke Test** — 5 steps with exact commands: boot, `docker compose ps`, MQTT publish, HTTPS dashboard, TimescaleDB query
- **Common Mistakes** — 5 bullets: WiFi vs Ethernet, wrong PSU, SD card for DB, hardcoded credentials, no static IP

### docs/hardware/power.md

Power distribution guide for the 12V outdoor infrastructure:

- **Strategy section** — Single cable run approach explained with ASCII block diagram
- **Parts Needed** — Links to BOM Section 5 for all 8 power/enclosure components
- **Wiring Table (garden nodes)** — 11-row table for full 12V → relay/solenoid/buck converter → Pi circuit
- **Buck Converter Setup** — 5-step procedure to adjust LM2596 to exactly 5.1V before connecting Pi (T-06-07 mitigation)
- **Wiring Table (hub/coop)** — Simplified 2-row table for official PSU direct connection
- **Enclosure Weatherproofing** — 6-step PG7 cable gland and IP65 enclosure procedure
- **Config File Cross-Reference** — Documents hardware-only components with no software config
- **Smoke Test** — 5 steps: buck converter bench test → load test → relay board power → enclosure seal → 12V output measurement
- **Common Mistakes** — 5 bullets: unadjusted buck converter, thin wire, IP65 misunderstanding, AC mains safety, PSU capacity

## Threat Model Compliance

| Threat | Mitigation | Location |
|--------|------------|----------|
| T-06-06 (MQTT_BRIDGE_PASS disclosure) | Documented as "Generate via generate-passwords.sh — do not hardcode"; security note added | hub.md Config Cross-Reference + Common Mistakes |
| T-06-07 (incorrect buck converter voltage damages Pi) | Step 1 of smoke test requires measuring and adjusting to 5.1V before connecting Pi; explicit warning block added | power.md Smoke Test + Buck Converter Setup section |

## Deviations from Plan

None — plan executed exactly as written.

The hub doc template was adapted as specified in the plan: "Wiring Table" became "Physical Assembly" and "GPIO Pin Assignment Table" became "Network Configuration" since the hub has no GPIO sensor connections. This was an explicit instruction in the plan, not a deviation.

## Known Stubs

None — both documents provide complete, actionable content. The Fritzing diagram reference in power.md (`fritzing/power-distribution.png`) points to a placeholder file already tracked in the `fritzing/` directory per the build-order established in plan 06-01. The wiring tables in the document provide all connection information independently of the diagram.

## Self-Check: PASSED

- docs/hardware/hub.md exists: FOUND
- docs/hardware/power.md exists: FOUND
- Commit bfa6c8d exists: FOUND
- Commit b42d2e1 exists: FOUND
- grep "config/hub.env" hub.md returns 13 matches (>3 required): PASSED
- grep "MQTT_BRIDGE_PASS" hub.md mentions generate-passwords.sh: PASSED
- grep "5.1V" power.md returns match: PASSED
- grep "LM2596" power.md returns 18 matches: PASSED
- Smoke Test present in both docs: PASSED
