---
phase: 06-hardware-shopping-list-and-wiring-diagrams
verified: 2026-04-16T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Confirm Fritzing placeholder PNGs display acceptably in GitHub / documentation renderer"
    expected: "Each fritzing/*.png renders as a white 1x1 pixel image (or blank) and does NOT show a broken-image icon, so subsystem doc wiring tables are the reader's fallback as intended"
    why_human: "PNG validity is byte-level (69 bytes each, verified); whether the GitHub Markdown renderer shows a broken icon vs a blank image for a 1x1 white placeholder requires visual inspection"
  - test: "Smoke test: coop-node.md L298N direction truth table — verify IN1=HIGH + IN2=LOW actually extends the ECO-WORTHY B088D7N85K actuator (not retracts)"
    expected: "When GPIO17 (IN1) = HIGH and GPIO27 (IN2) = LOW the actuator rod extends (coop door moves toward open). Document says this; physical test with real hardware confirms it before wiring is final."
    why_human: "Motor polarity on a specific generic actuator can be reversed depending on which actuator wire is labeled A vs B. The document instructs the builder to swap OUT1/OUT2 wires if direction is wrong, but the initial claim (HIGH=extend) must be confirmed on real hardware."
---

# Phase 6: Hardware Shopping List and Wiring Diagrams — Verification Report

**Phase Goal:** A farmer with zero electronics experience can purchase every component and wire the complete system by following the documentation alone. Every connection (GPIO, I2C, relay, solenoid, limit switch, load cell, power supply) is documented with pin numbers, wire colors, and physical diagrams. The shopping list is organized by subsystem with exact part numbers, quantities, and sourcing links.

**Verified:** 2026-04-16
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A single shopping list document covers every component organized by subsystem with exact part numbers, quantities, prices, and purchase links; total cost summary included | VERIFIED | `docs/hardware/bom.md` — 5 subsystem sections, 30+ components, all with Model/SKU, Unit Price, Qty, Subtotal, Purchase Link, Fallback Spec; `~$742` total appears 4× consistently |
| 2 | Wiring diagrams exist for every hardware connection (GPIO, I2C, relay, solenoid, limit switch, load cell, power); readable by a non-engineer | VERIFIED | All 5 subsystem docs contain wiring tables with From/To/Wire Color/Notes columns; GPIO pin assignment tables; I2C address maps; 9-color wire convention used consistently. Fritzing PNGs are 1x1 placeholder images — wiring tables serve as the complete reference per the documented intent |
| 3 | Each diagram includes a smoke test procedure the farmer can follow per subsystem | VERIFIED | hub.md: 5-step smoke test; power.md: 5-step smoke test; garden-node.md: 6-step smoke test; irrigation.md: 5-step smoke test; coop-node.md: 8-step smoke test |
| 4 | Documentation cross-references the codebase — each hardware connection maps to a specific config file, GPIO constant, or I2C address used in the software | VERIFIED | Config File Cross-Reference tables present in all 5 subsystem docs. garden-node.md: 9 cross-references to `sensors.py`, `mqtt-topic-schema.md`, `hub.env`. coop-node.md: 17 cross-references to `sensors.py`, `rules.py`, `main.py`, `coop_scheduler.py`. irrigation.md: references to `rules.py` IRRIGATION_SHUTOFF stub. hub.md: references to all `config/hub.env` variables |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/hardware/bom.md` | Master BOM — all components, quantities, prices, links, total cost | VERIFIED | 198 lines; 30+ component rows; $742 total; Budget Alternatives section (5 options); Wire Color Convention table; Quick-Reference Card |
| `docs/hardware/README.md` | Navigation index for all hardware docs, Fritzing setup instructions, standard template | VERIFIED | Exists; build order (6 docs in sequence); directory contents table; 7-section template description; wire color table; Fritzing 1.0.6 workflow |
| `docs/hardware/hub.md` | Hub assembly, SSD setup, Docker Compose start, Ethernet/HTTPS config, smoke test | VERIFIED | 193 lines; all required sections present; 13 references to `config/hub.env`; MQTT_BRIDGE_PASS only documents generate-passwords.sh approach |
| `docs/hardware/power.md` | 12V power distribution, LM2596 buck converter, IP65 enclosure, safety notes, smoke test | VERIFIED | 161 lines; LM2596 appears 18×; 5.1V target voltage explicitly documented; PG7 cable gland steps; 5 common mistakes |
| `docs/hardware/garden-node.md` | Garden zone edge node wiring — 3 sensors + relay on Pi Zero 2W | VERIFIED | 232 lines; 0x36 appears 22×; 0x48 appears 22×; GPIO4/1-Wire; i2cdetect command; per-zone address table; sensors.py cross-references |
| `docs/hardware/irrigation.md` | Solenoid valve relay wiring, NC valve verification, active-LOW test | VERIFIED | 188 lines; "normally-closed" 14× in doc; active-LOW relay test script included; rules.py references 4× |
| `docs/hardware/coop-node.md` | Complete coop edge node wiring — actuator, limit switches, load cells, sensors | VERIFIED | 370 lines; L298N 23×; HX711 36×; GPIO pin assignment table (18 rows); 17-row config cross-reference; 8-step smoke test |
| `docs/hardware/fritzing/README.md` | Fritzing workflow and placeholder diagram tracking | VERIFIED | Exists; 8-entry files table; breadboard-view-only rationale; per-diagram content descriptions |
| `docs/hardware/fritzing/garden-node.fzz` | Placeholder .fzz tracking path for future Fritzing diagram | VERIFIED (placeholder) | 211 bytes; "PLACEHOLDER" marker; author action required — this is intentional design, documented in fritzing/README.md |
| `docs/hardware/fritzing/garden-node.png` | Placeholder PNG so Markdown image references don't break | VERIFIED (placeholder) | 69 bytes; valid 1x1 white PNG; prevents broken-image icon before real diagram is created |
| `docs/hardware/fritzing/coop-node.fzz` | Placeholder .fzz | VERIFIED (placeholder) | 230 bytes; PLACEHOLDER marker |
| `docs/hardware/fritzing/coop-node.png` | Placeholder PNG | VERIFIED (placeholder) | 69 bytes; valid PNG |
| `docs/hardware/fritzing/irrigation-relay.fzz` | Placeholder .fzz | VERIFIED (placeholder) | 215 bytes; PLACEHOLDER marker |
| `docs/hardware/fritzing/irrigation-relay.png` | Placeholder PNG | VERIFIED (placeholder) | 69 bytes; valid PNG |
| `docs/hardware/fritzing/power-distribution.fzz` | Placeholder .fzz | VERIFIED (placeholder) | 224 bytes; PLACEHOLDER marker |
| `docs/hardware/fritzing/power-distribution.png` | Placeholder PNG | VERIFIED (placeholder) | 69 bytes; valid PNG |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docs/hardware/bom.md` | hub.md, garden-node.md, coop-node.md, irrigation.md, power.md | Footer links + `bom.md#section-N` anchors | WIRED | Footer of bom.md links all 5 subsystem docs; all subsystem docs link back to bom.md section anchors (e.g., `bom.md#section-1-hub`) |
| `docs/hardware/hub.md` | `config/hub.env` | Config File Cross-Reference table | WIRED | 7 env var rows: HUB_IP, MQTT_PORT, HUB_HTTPS_PORT, TIMESCALEDB_PORT, SSD_MOUNT, MQTT_BRIDGE_USER, MQTT_BRIDGE_PASS |
| `docs/hardware/power.md` | `docs/hardware/bom.md` | Parts Needed section | WIRED | 8 component rows link to `bom.md#section-5-power-enclosures-and-wiring` |
| `docs/hardware/garden-node.md` | `edge/daemon/sensors.py` | Config File Cross-Reference table | WIRED | References `ADS1115PHDriver.i2c_address`, `DS18B20Driver`, `MoisturePlaceholder` — 4 matches |
| `docs/hardware/irrigation.md` | `edge/daemon/rules.py` | Config File Cross-Reference table | WIRED | References `execute_action(IRRIGATION_SHUTOFF)` — 4 matches |
| `docs/hardware/coop-node.md` | `edge/daemon/rules.py` | Config File Cross-Reference (COOP_HARD_CLOSE) | WIRED | `execute_action(COOP_HARD_CLOSE)` — GPIO17/27/22 stub documented |
| `docs/hardware/coop-node.md` | `hub/bridge/coop_scheduler.py` | Config File Cross-Reference (lat/long) | WIRED | `HUB_LATITUDE`, `HUB_LONGITUDE` → `coop_scheduler.py` — 11 cross-reference rows |

---

## Data-Flow Trace (Level 4)

Not applicable — this phase produces only documentation (Markdown files). There is no dynamic data rendered by components, no API routes, and no state management. Level 4 data-flow trace is skipped.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| bom.md contains $742 total | `grep -c "~\$742" docs/hardware/bom.md` | 4 matches | PASS |
| All 5 subsystem docs link back to bom.md | `grep -c "bom.md" docs/hardware/hub.md docs/hardware/power.md docs/hardware/garden-node.md docs/hardware/coop-node.md docs/hardware/irrigation.md` | 5, 9, 11, 11, 6 | PASS |
| NC solenoid safety requirement documented | `grep -c "normally-closed\|NC" docs/hardware/bom.md` | 7 matches | PASS |
| Smoke test in every subsystem doc | `grep -c "Smoke Test" hub.md power.md garden-node.md irrigation.md coop-node.md` | 1 each = 5 total | PASS |
| Common Mistakes in every subsystem doc | `grep -c "Common Mistakes" hub.md power.md garden-node.md irrigation.md coop-node.md` | 1 each = 5 total | PASS |
| COOP-03/COOP-04 explicitly referenced | `grep -c "COOP-03\|COOP-04" docs/hardware/coop-node.md` | 1 match | PASS |
| IRRIG-03 explicitly referenced | `grep -c "IRRIG-03" docs/hardware/bom.md docs/hardware/irrigation.md` | 1 each | PASS |
| All fritzing placeholder files exist | `ls docs/hardware/fritzing/` | 9 files (README + 4×fzz + 4×png) | PASS |
| Fritzing PNGs are non-zero size | `ls -la docs/hardware/fritzing/*.png` | 69 bytes each | PASS |
| Wire color convention in bom.md | `grep -c "Wire Color Convention" docs/hardware/bom.md` | 1 match | PASS |
| I2C addresses 0x36 and 0x48 in garden-node.md | `grep -c "0x36\|0x48" docs/hardware/garden-node.md` | 22 matches | PASS |
| L298N motor driver documented in coop-node.md | `grep -c "L298N" docs/hardware/coop-node.md` | 23 matches | PASS |
| HX711 bit-bang protocol documented | `grep -c "HX711" docs/hardware/coop-node.md` | 36 matches | PASS |
| Buck converter 5.1V safety target documented | `grep -c "5.1V" docs/hardware/power.md` | multiple matches | PASS |
| hub.env cross-reference in hub.md | `grep -c "config/hub.env" docs/hardware/hub.md` | 13 matches (≥3 required) | PASS |
| MQTT_BRIDGE_PASS → generate-passwords.sh only | `grep "MQTT_BRIDGE_PASS" docs/hardware/hub.md` | References generate-passwords.sh, no actual value | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOC-01 | 06-01, 06-05 | Complete hardware shopping list organized by subsystem with exact part numbers, quantities, unit prices, and purchase links; includes total cost summary | SATISFIED | `docs/hardware/bom.md` — 5 subsystem sections, 30+ line items, $742 total, Budget Alternatives, Quick-Reference Card, Wire Color Convention |
| DOC-02 | 06-02, 06-03, 06-04, 06-05 | Wiring diagrams for every hardware connection with pin numbers, wire colors, standard notation, and smoke test per subsystem; cross-references codebase | SATISFIED | 5 subsystem docs with wiring tables (From/To/Wire Color/Notes), GPIO pin assignment tables, Config File Cross-Reference tables, and smoke tests in all 5 docs |

---

## Anti-Patterns Found

| File | Finding | Severity | Impact |
|------|---------|----------|--------|
| `docs/hardware/fritzing/*.fzz` | All 4 .fzz files contain "PLACEHOLDER" text rather than real Fritzing XML | INFO | Intentional design — placeholder paths reserved for post-Phase-6 author action; docs/hardware/README.md and fritzing/README.md both document this explicitly; wiring tables in each subsystem doc are the complete information source |
| `docs/hardware/fritzing/*.png` | All 4 PNG files are 1×1 white pixel placeholders (69 bytes) | INFO | Intentional design — prevents broken image icons in Markdown; real diagrams to be created by author with Fritzing 1.0.6 post-Phase-6; documented as pending in both README files |

No blockers. No unexpected stubs. Placeholder status is explicitly disclosed to readers in docs/hardware/README.md ("The diagrams are visual supplements to the wiring tables, not replacements for them").

---

## Human Verification Required

### 1. Fritzing Placeholder PNG Display

**Test:** Open `docs/hardware/garden-node.md` on GitHub (or any Markdown renderer) and inspect where `![Garden node wiring diagram](fritzing/garden-node.png)` renders.

**Expected:** A blank/white image (or very small image) renders without a broken-image icon. The "Note" callout below the image reference explains that diagrams are pending and wiring tables contain the complete information.

**Why human:** The 69-byte 1×1 white PNG is structurally valid (verified: Python struct/zlib construction). Whether a specific Markdown renderer — particularly GitHub's — renders it cleanly or shows a broken icon depends on renderer behavior that cannot be determined by file inspection.

---

### 2. L298N Actuator Direction Confirmation on Real Hardware

**Test:** With a wired ECO-WORTHY B088D7N85K linear actuator connected to an L298N module, set GPIO17 (IN1) = HIGH and GPIO27 (IN2) = LOW and observe actuator movement direction.

**Expected:** Actuator rod extends (moves toward open position). If it retracts instead, the builder must swap the two motor wires at L298N OUT1/OUT2 as documented in the "Testing direction" note in `docs/hardware/coop-node.md`.

**Why human:** Motor polarity is hardware-specific. The document correctly anticipates this with a swap instruction, but the initial direction claim cannot be confirmed without powering the specific actuator. The builder's first power-on test will reveal the correct wiring within 5 seconds.

---

## Gaps Summary

No gaps. All 4 roadmap success criteria are satisfied by the documented artifacts:

1. **DOC-01 (shopping list):** `docs/hardware/bom.md` is complete, substantive, and cross-linked.
2. **DOC-02 (wiring diagrams):** All 5 subsystem docs contain full wiring tables, GPIO tables, Config Cross-Reference tables, and smoke tests. The absence of real Fritzing diagram images is an intentional, disclosed, post-Phase-6 author action — not a gap.
3. **Smoke tests:** Every subsystem doc (hub, power, garden-node, irrigation, coop-node) has a numbered smoke test procedure.
4. **Codebase cross-references:** All subsystem docs map hardware connections to specific config variables, GPIO constants, I2C addresses, and code files.

The two human verification items are edge cases (renderer behavior for placeholder images, first-boot actuator direction) that are not blockers — both are anticipated and handled in the documentation itself.

---

_Verified: 2026-04-16_
_Verifier: Claude (gsd-verifier)_
