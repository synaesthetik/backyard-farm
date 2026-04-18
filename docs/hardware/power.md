# Power Distribution

The backyard farm platform uses two voltage levels:

- **5V DC** — Powers all Raspberry Pi nodes (via USB-C or LM2596 buck converter)
- **12V DC** — Powers solenoid valves, relay boards, and the linear actuator

## Strategy: Single Cable Runs to Outdoor Nodes

Each outdoor garden zone node needs both 5V (for the Pi Zero 2W) and 12V (for the
solenoid valve and relay board). Running two separate power cables per node gets messy.
Instead, run a single 12V cable to each node, then use an LM2596 buck converter inside
the node's enclosure to step 12V down to 5V for the Pi.

```
AC mains
  └── 12V 5A IP65 PSU (weatherproof, mounted indoors or in weatherproof box)
        ├── 12V → relay board (powers relay coils)
        ├── 12V → solenoid valve (via relay COM/NC)
        └── 12V → LM2596 buck converter → 5V → Pi Zero 2W USB-C input
```

The hub and coop node use dedicated official Raspberry Pi PSUs (5V/5A USB-C) since
they are near AC outlets and do not need to share a power line with solenoid valves.

## Parts Needed

From the [Master BOM](bom.md):

| Component | BOM Section | Qty |
|-----------|------------|-----|
| 12V 5A IP65 waterproof DC power supply | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 5 |
| Raspberry Pi 5 Official PSU 5V/5A | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 2 |
| LM2596 DC-DC buck converter | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 4 |
| IP65 ABS project enclosure ~150×100×70mm | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 6 |
| PG7 cable gland | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 1 pack |
| 18AWG stranded wire assortment | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 1 |
| Wago 221 lever connectors | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 1 pack |
| Heat shrink tubing assortment | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | 1 |

## Overview Diagram

![Power distribution wiring diagram](fritzing/power-distribution.png)
Source: `docs/hardware/fritzing/power-distribution.fzz`

> **Note:** The diagram above shows the power distribution for one garden node.
> Repeat the same pattern for all 4 garden nodes. The hub and coop node use
> direct USB-C PSU connections (no 12V rail or buck converter needed).

## Wiring Table — Garden Node Power (per node ×4)

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| AC mains IN | Wall outlet | 12V 5A PSU input | — | Use PSU's included AC cable; follow local electrical code |
| 12V DC out (positive) | 12V PSU + terminal | Wago connector (12V bus) | Orange | 18AWG minimum |
| 12V DC out (negative) | 12V PSU − terminal | Wago connector (GND bus) | Black | 18AWG minimum |
| 12V to relay board | Wago 12V bus | Relay board DC+ | Orange | Powers relay coils |
| GND to relay board | Wago GND bus | Relay board DC− | Black | |
| 12V to buck converter IN | Wago 12V bus | LM2596 IN+ | Orange | Input to step-down converter |
| GND to buck converter IN | Wago GND bus | LM2596 IN− | Black | |
| 5V from buck converter OUT | LM2596 OUT+ | Pi Zero 2W USB-C (+5V) | Red | Adjust buck converter output to exactly 5.1V before connecting Pi |
| GND from buck converter OUT | LM2596 OUT− | Pi Zero 2W USB-C (GND) | Black | |
| 12V to solenoid (via relay) | Relay COM terminal | Solenoid valve (+) | Orange | Relay switches 12V to solenoid |
| GND to solenoid | Wago GND bus | Solenoid valve (−) | Black | Solenoid return path |

## Setting Buck Converter Output Voltage

**Before connecting the Pi Zero 2W**, set the LM2596 output to exactly 5.1V:

1. Connect the LM2596 to 12V (only — no Pi connected yet)
2. Measure the output with a multimeter on the OUT+ and OUT− terminals
3. Turn the small blue trimmer potentiometer on the LM2596 until you read 5.1V
4. Clockwise = voltage decreases, Counter-clockwise = voltage increases (varies by module — check by measuring)
5. Once set: disconnect 12V, connect the Pi Zero 2W USB-C cable, reconnect 12V

> **Warning:** Do not connect a Raspberry Pi to an unregulated or incorrectly set buck
> converter. Output above 5.25V will damage the Pi. Output below 4.75V will cause
> undervoltage throttling and instability.

## Wiring Table — Hub and Coop Node Power

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| AC mains | Wall outlet | Raspberry Pi 5 Official PSU | — | Use official PSU only (27W, 5V/5A) |
| 5V DC | Official PSU USB-C out | Pi 5 USB-C port | — | Included cable; no modification needed |

Hub and coop node need no 12V power — they run entirely on 5V from the official PSU.

## Enclosure Weatherproofing

Every outdoor node (4 garden nodes + 1 coop node + wiring junction boxes as needed)
must be enclosed in an IP65-rated project box.

| Step | Action |
|------|--------|
| 1 | Drill cable entry holes sized for PG7 glands (~12mm for PG7) |
| 2 | Thread PG7 cable gland into hole from outside; tighten with lock nut inside |
| 3 | Route 12V cable through gland; tighten gland body to grip cable jacket |
| 4 | Mount Pi Zero 2W, relay board, and LM2596 inside enclosure using M2.5 standoffs |
| 5 | Secure lid — IP65 boxes have silicone gaskets; verify gasket is seated before closing |
| 6 | Mount enclosure at least 30cm above expected flood/splash height |

## Config File Cross-Reference

| Hardware | Config Variable | File | Notes |
|----------|-----------------|------|-------|
| Hub PSU output | HUB_IP | `config/hub.env` | Hub IP set here; PSU hardware not configured in software |
| Buck converter 5V output | (none) | Hardware-only | Adjusted physically; no software config |
| 12V solenoid voltage | (none) | Hardware-only | Solenoid rated 12V; relay board connects from 12V bus |

## Smoke Test

Perform before connecting any Pi, sensor, or actuator to the power rails.

**Step 1 — Bench test buck converter (no load)**
1. Connect LM2596 IN+ to 12V PSU positive terminal
2. Connect LM2596 IN− to 12V PSU negative terminal
3. Measure LM2596 OUT+ with multimeter — target: 5.1V
4. Adjust trimmer until multimeter reads 5.1V

**Step 2 — Load test buck converter**
1. Connect a 5V/0.5A test load (e.g., USB LED light) to LM2596 output
2. Measure output under load — should remain above 4.9V
3. If voltage drops significantly under light load, module may be defective — replace

**Step 3 — Relay board power test (no actuator)**
1. Connect relay board DC+ to 12V bus, DC− to GND bus
2. The relay board's power LED should illuminate (if present)
3. Do NOT connect any actuator (valve, motor) yet — relay test is in the irrigation/coop docs

**Step 4 — Verify enclosure seal**
1. Close enclosure lid with all cables routed through PG7 glands
2. Gently tug each cable — it should not slide through the gland
3. Visually inspect gasket seal around entire lid perimeter

**Step 5 — Measure 12V PSU output**
1. With everything connected (relay board + LM2596 + Pi load simulated)
2. Measure 12V PSU output terminals — should read 11.8V–12.5V
3. If below 11.5V under load, PSU is undersized — replace with 10A model

## Common Mistakes

- **Not adjusting the buck converter before connecting the Pi** — The factory default output
  on LM2596 modules varies from 1.25V to 35V. Always measure and adjust to 5.1V before
  connecting any load. Sending 12V to a Pi will destroy it instantly.

- **Using thin wire (26AWG or smaller) for 12V power runs** — The 12V solenoid valves draw
  up to 500mA each. Use 18AWG or heavier for all 12V power runs. Signal wires (GPIO to
  relay) can be 22AWG.

- **Forgetting IP65 means splash-proof, not submersion-proof** — Mount enclosures under
  eaves or overhangs. A direct hose spray can force water past PG7 glands. Point cable
  entries downward when possible so water drains away rather than into the gland.

- **Routing AC mains wiring yourself** — The 12V PSU connects to AC mains on one side.
  Use only PSUs with safety certifications (CE, UL, etc.) and intact AC connectors. Do not
  splice or extend the AC-side wiring without proper wire nuts and electrical tape.

- **Sharing the 12V bus across too many nodes without checking PSU capacity** — Each node
  with a solenoid valve can draw up to 700mA (500mA solenoid + 200mA relay board).
  A 5A supply can handle up to 7 nodes. One PSU per 2–3 nodes is safer.
