# Phase 6: Hardware Shopping List and Wiring Diagrams - Research

**Researched:** 2026-04-16
**Domain:** Hardware documentation — BOM, Fritzing wiring diagrams, Raspberry Pi GPIO, I2C/1-Wire/SPI sensors, relay/solenoid/actuator wiring, smoke tests
**Confidence:** HIGH (component specs and GPIO pinout), MEDIUM (current pricing — volatile due to RAM shortage), LOW (individual unit prices not confirmed at checkout)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Hardware platform:**
- D-01: Garden zone edge nodes: Raspberry Pi Zero 2W (~$15 MSRP; currently ~$17.25 at PiShop)
- D-02: Coop edge node: Raspberry Pi 4 or 5 (more GPIO, runs ONNX inference, handles motor control + limit switches + load cell + multiple sensors)
- D-03: Hub: Raspberry Pi 4 or 5 with 8GB RAM (runs Docker Compose stack; currently ~$175 at PiShop due to RAM price crisis)
- D-04: Budget target: under $500 total for the complete system (hub + 4 garden nodes + 1 coop node + all sensors, actuators, wiring, enclosures)

**Diagram format and tooling:**
- D-05: Fritzing breadboard-style diagrams for all wiring. Non-engineers understand these instantly.
- D-06: Source `.fzz` files committed to the repo under `docs/hardware/fritzing/`
- D-07: Rendered PNG images embedded in the Markdown docs for easy viewing on GitHub

**Document structure:**
- D-08: All hardware docs live in `docs/hardware/` in the repo (Markdown + images)
- D-09: Organized by physical location:
  - `docs/hardware/bom.md` — Master shopping list
  - `docs/hardware/hub.md` — Hub assembly and wiring
  - `docs/hardware/garden-node.md` — Garden zone edge node (template for all 4 zones)
  - `docs/hardware/coop-node.md` — Coop edge node (motor, limit switches, load cell, sensors)
  - `docs/hardware/irrigation.md` — Solenoid valves, relay wiring, water supply
  - `docs/hardware/power.md` — Power supply distribution, voltage regulators, protection

**Sourcing philosophy:**
- D-10: Each component gets an exact primary recommendation with purchase link
- D-11: Each component also gets a generic fallback spec description
- D-12: Include a "total cost" summary in bom.md with per-subsystem breakdown

### Claude's Discretion

- Specific sensor module choices (researcher should recommend best value-for-money options)
- Exact GPIO pin assignments (planner can optimize for physical layout)
- Wire color conventions (follow standard practices)
- Enclosure/weatherproofing recommendations
- Smoke test procedure specifics for each subsystem

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | A complete hardware shopping list organized by subsystem with exact part numbers, quantities, unit prices, and purchase links; includes total cost summary | Component inventory below covers all 6 subsystems; pricing researched; Adafruit/Amazon links identified |
| DOC-02 | Wiring diagrams for every hardware connection (GPIO, I2C, relay, solenoid, limit switch, load cell, power) with pin numbers, wire colors, standard notation, and smoke test per subsystem; cross-references codebase config files and constants | GPIO pinout, I2C addresses, and sensor drivers confirmed in codebase; Fritzing workflow documented |
</phase_requirements>

---

## Summary

Phase 6 is a pure documentation phase — no application code is written. The deliverable is a set of Markdown files under `docs/hardware/` that enable a person with zero electronics experience to purchase every component and wire the complete system. The research here provides two things the planner needs: (1) a complete verified component list with technical specs the planner can write directly into `bom.md`, and (2) a wiring documentation pattern the planner can use to structure each subsystem doc.

The most important discovery from reading the existing codebase: the moisture sensor driver is explicitly a placeholder (`MoisturePlaceholder`) in `edge/daemon/sensors.py`, with a comment that the sensor model is "TBD per D-01 research spike." Phase 6 must make a definitive recommendation here. The Adafruit STEMMA Soil Sensor (product 4026, $7.50) is the best-value I2C capacitive option — it supports 4 addresses (0x36–0x39), eliminating the need for the TCA9548A multiplexer on garden nodes. This resolves the D-01/D-05 open question from Phase 1.

The Fritzing tooling decision requires careful handling: the official binaries at fritzing.org cost at minimum €8 (a contribution, not subscription), but the source code is GPL v3 and can be built freely. The planner should instruct the author to download Fritzing 1.0.6 (latest stable, December 2025) from the official site. Alternatively, the diagrams could be created in a web tool if the author prefers not to install Fritzing. The `.fzz` source files committed per D-06 allow future contributors to edit diagrams.

**Budget alert:** The D-04 budget target of under $500 is tight given current Raspberry Pi pricing (RAM shortage in 2026). The Pi 5 8GB for the hub is ~$175; four Pi Zero 2W nodes are ~$69; one Pi 4/5 for coop is ~$60–$175 depending on model. Component and sensor costs add up quickly. The planner must calculate a realistic total and flag if the $500 target is at risk. See "Budget Constraint Analysis" below.

**Primary recommendation:** Use Adafruit STEMMA Soil Sensor (I2C, 4 selectable addresses) for moisture; use Fritzing 1.0.6 for diagrams; document each subsystem with the standard pattern (parts, wiring diagram, pin table, smoke test, common mistakes, code cross-reference).

---

## Standard Stack

### Hardware — Compute Nodes

| Component | Model | Unit Price | Quantity | Subtotal | Purpose |
|-----------|-------|-----------|----------|----------|---------|
| Raspberry Pi Zero 2W | SC1146 | ~$17 | 4 | ~$68 | Garden zone edge nodes |
| Raspberry Pi 5 4GB | SC1112 | ~$60 | 1 | ~$60 | Coop edge node (ONNX inference capable) |
| Raspberry Pi 5 8GB | SC1112 | ~$175 | 1 | ~$175 | Hub (Docker Compose stack) |
| Micro SD card 32GB A2 (Samsung Pro Endurance) | MB-MJ32KA | ~$12 | 5 | ~$60 | Edge node OS storage |
| Raspberry Pi M.2 HAT+ | SC1166 | ~$12 | 1 | ~$12 | Hub NVMe attachment |
| M.2 NVMe SSD 256GB | various | ~$30 | 1 | ~$30 | Hub TimescaleDB storage (SSD required) |

Note on coop node: Pi 5 4GB (~$60) is recommended over Pi 4 — same price tier after RAM hikes, better performance for ONNX inference. The Pi 4 8GB would cost more than the Pi 5 4GB at current prices. [VERIFIED: PiShop pricing April 2026, Tom's Hardware RAM shortage reporting]

### Hardware — Garden Zone Sensors (per node × 4)

| Component | Model/SKU | Unit Price | Per Node | 4 Nodes | Purpose |
|-----------|-----------|-----------|----------|---------|---------|
| Adafruit STEMMA Soil Sensor | ID 4026 | $7.50 | 1 | $30 | Soil moisture VWC % via I2C |
| Adafruit ADS1115 16-bit ADC | ID 1085 | $14.95 | 1 | $60 | pH probe analog-to-digital |
| DS18B20 waterproof probe | ID 381 | ~$4.00 | 1 | $16 | Soil temperature (1-Wire) |
| 4.7kΩ resistor | generic | ~$0.10 | 1 | ~$0.40 | DS18B20 pull-up resistor |
| Analog pH probe + BNC connector | DFRobot SEN0161-V2 | ~$10 | 1 | $40 | pH measurement |
| JST PH 2mm 4-pin cable | generic | ~$0.50 | 1 | $2 | STEMMA soil sensor connection |
| Jumper wire kit | generic | ~$5 total | shared | $5 | All GPIO connections |

Note: Adafruit STEMMA Soil Sensor (I2C, addresses 0x36–0x39 via solder jumpers) resolves the D-01 moisture sensor question left open from Phase 1. Four sensors can share one I2C bus without a multiplexer. [VERIFIED: adafruit.com/product/4026, learn.adafruit.com pinouts page]

### Hardware — Coop Node Sensors and Actuators

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purpose |
|-----------|-----------|-----------|-----|----------|---------|
| HX711 + 5kg load cell kit | generic (Amazon) | ~$10 | 1 | $10 | Feed hopper weight |
| HX711 + 5kg load cell kit | generic (Amazon) | ~$10 | 1 | $10 | Nesting box weight (Phase 3) |
| Water level sensor (float switch) | generic | ~$5 | 1 | $5 | Coop water level |
| DS18B20 waterproof probe | ID 381 | ~$4 | 1 | $4 | Coop temperature |
| 4.7kΩ resistor | generic | ~$0.10 | 1 | $0.10 | DS18B20 pull-up |
| ECO-WORTHY 12V linear actuator | B088D7N85K | ~$35 | 1 | $35 | Coop door motor (built-in limit switches) |
| Limit switch (normally-open) | generic roller type | ~$1.50 | 2 | $3 | Physical door position confirmation (COOP-03, COOP-04) |
| L298N motor driver module | generic | ~$3 | 1 | $3 | Linear actuator H-bridge control |
| 4-channel relay board 5V optocoupler | generic | ~$6 | 1 | $6 | Irrigation valve control (coop has no valves but relays support expansion) |

Note: The ECO-WORTHY actuator has internal limit switches that stop motor at end of stroke. The system also requires EXTERNAL limit switches for software position confirmation (COOP-03 requires "physical limit switch confirmation" via GPIO, not motor stall detection). [ASSUMED — two separate limit switch mechanisms needed; COOP-03 is explicit in requirements]

### Hardware — Irrigation (Shared Infrastructure)

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purpose |
|-----------|-----------|-----------|-----|----------|---------|
| 3/4" NC solenoid valve 12V DC | U.S. Solid (ussolid.com) | ~$12 | 4 | $48 | One per garden zone, normally-closed (IRRIG-03) |
| 4-channel relay board 5V optocoupler | generic | ~$6 | 1 | $6 | Valve control per zone node (one relay = one valve) |
| 3/4" garden hose Y-splitter | generic | ~$8 | 1 | $8 | Water supply manifold |
| Hose to NPT adapter 3/4" | generic | ~$3 | 4 | $12 | Solenoid inlet connection |

Important: Solenoids MUST be confirmed normally-closed (NC) — valve closed when unpowered. The U.S. Solid 3/4" NC model is explicitly NC with Viton seal, suitable for irrigation. [VERIFIED: ussolid.com product listings]

### Hardware — Power Distribution

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purpose |
|-----------|-----------|-----------|-----|----------|---------|
| 12V 5A DC power supply (IP65) | various | ~$15 | 1 (per outdoor node) | ~$75 | Powers solenoids + relay boards at outdoor locations |
| Raspberry Pi 5 official PSU 5V 5A | SC1155 | $12 | 2 | $24 | Hub and coop node power |
| Raspberry Pi Zero 2W USB power (5V 2A) | generic USB-C | ~$8 | 4 | $32 | Garden node power |
| DC-DC buck converter 12V→5V | generic LM2596 | ~$3 | 4 | $12 | Power Pi Zero from 12V rail (single cable run) |
| IP65 ABS project enclosure (small) | ~150×100×70mm | ~$8 | 6 | $48 | Weatherproof each outdoor node |
| Cable gland PG7 | generic 10-pack | ~$5 | 1 | $5 | Strain relief through enclosure |
| 18AWG stranded wire assortment (red/black/colors) | generic | ~$15 | 1 | $15 | Power wiring |
| 22AWG dupont jumper wire assortment | generic | ~$8 | 1 | $8 | GPIO signal wiring |
| Heat shrink tubing assortment | generic | ~$5 | 1 | $5 | Wire insulation |
| Wire connectors (Wago 221 or equivalent) | generic | ~$10 | 1 | $10 | Splicing power runs |

Note: The DC-DC buck converter approach (12V supply → buck converter → 5V for Pi) allows a single outdoor cable run carrying 12V for both the solenoid valve and the Pi. Alternative: separate USB power cable run to each node. The buck converter approach is cleaner for outdoor installs. [ASSUMED — either approach works; planner can choose]

### Budget Constraint Analysis

Estimated total (all components, single quantity):

| Subsystem | Estimated Cost |
|-----------|---------------|
| Hub (Pi 5 8GB + M.2 HAT + NVMe SSD + PSU) | ~$232 |
| 4× Garden nodes (Pi Zero 2W + SD card + sensors) | ~$220 |
| 1× Coop node (Pi 5 4GB + SD card + sensors + actuator) | ~$130 |
| Irrigation (4× solenoid valves + relay boards) | ~$60 |
| Power + enclosures + wiring | ~$100 |
| **ESTIMATED TOTAL** | **~$742** |

This significantly exceeds the D-04 budget target of $500. [ASSUMED — prices verified individually but not confirmed in a single cart; actual total may vary by ±20%]

The planner must address this budget gap explicitly. Options to discuss with the user:
1. Use Raspberry Pi 4B 2GB (~$35) for the coop node instead of Pi 5 — ONNX inference still works
2. Share one 12V supply across multiple nodes instead of one per node
3. Stage procurement: hub + 1 garden node first, expand over time
4. Source sensors from AliExpress at 30-50% lower cost (longer shipping, variable quality)

The planner should NOT silently downscope below what the codebase requires. Flag the budget constraint explicitly in `bom.md` with a note for the user.

---

## Architecture Patterns

### Document Structure (Locked, D-09)

```
docs/
└── hardware/
    ├── bom.md                  # Master shopping list — all components, costs, links
    ├── hub.md                  # Hub: Pi 5 8GB + SSD + Docker Compose
    ├── garden-node.md          # Garden zone node (template for zones 1-4)
    ├── coop-node.md            # Coop node: actuator, load cell, sensors
    ├── irrigation.md           # Solenoid valves, relay wiring, water supply
    ├── power.md                # Power distribution, buck converters, safety
    └── fritzing/               # Fritzing source files (D-06)
        ├── garden-node.fzz
        ├── coop-node.fzz
        ├── irrigation-relay.fzz
        └── power-distribution.fzz
```

Images referenced from Markdown are stored alongside `.fzz` sources in `docs/hardware/fritzing/` as PNG exports.

### Standard Subsystem Doc Template (D-09, per specifics section)

Every subsystem document (`hub.md`, `garden-node.md`, etc.) follows this exact structure:

```markdown
# [Subsystem Name]

## Parts Needed
Links back to bom.md for each component used in this subsystem.

## Overview Diagram
![wiring diagram](fritzing/[name].png)
Source: `docs/hardware/fritzing/[name].fzz`

## Wiring Table
| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 3.3V power | Pi GPIO Pin 1 | Soil sensor VIN | Red | ... |
| GND | Pi GPIO Pin 6 | Soil sensor GND | Black | ... |
| I2C SDA | Pi GPIO Pin 3 (GPIO2) | Soil sensor SDA | Blue | ... |
| I2C SCL | Pi GPIO Pin 5 (GPIO3) | Soil sensor SCL | Yellow | ... |

## GPIO Pin Assignment Table
| GPIO (BCM) | Physical Pin | Function | Connected To |
|------------|-------------|----------|-------------|
| GPIO2 | Pin 3 | I2C SDA | ADS1115 SDA, STEMMA SDA |
| GPIO3 | Pin 5 | I2C SCL | ADS1115 SCL, STEMMA SCL |
| GPIO4 | Pin 7 | 1-Wire data | DS18B20 DQ |

## Config File Cross-Reference
| Hardware Connection | Config Variable | File | Value |
|--------------------|-----------------|------|-------|
| I2C address, soil sensor zone-01 | hardcoded 0x36 | `edge/daemon/sensors.py` | 0x36 |
| pH ADC I2C address | hardcoded 0x48 | `edge/daemon/sensors.py` | 0x48 |
| 1-Wire GPIO pin | kernel default | `/boot/config.txt` | GPIO4 |
| MQTT host | MQTT_HOST | `config/hub.env` | 192.168.1.100 |

## Smoke Test
Step-by-step power-on verification before connecting next subsystem.

## Common Mistakes
Bulleted list of the 3-5 most common errors for this subsystem.
```

### Wire Color Convention (Standard Practice)

| Wire Color | Function |
|-----------|---------|
| Red | DC positive power (3.3V or 5V logic rails) |
| Orange | 12V DC power |
| Black | Ground / DC negative |
| Blue | I2C SDA |
| Yellow | I2C SCL |
| Green | GPIO signal / relay control |
| White | 1-Wire data |
| Gray | Relay COM |
| Purple | Relay NC (normally-closed contact) |

These follow hobbyist convention as described on pinout.xyz and Raspberry Pi forum guides. [VERIFIED: Raspberry Pi Forums wiring guide, pinout.xyz]

### GPIO Pin Assignments (Raspberry Pi Zero 2W and Pi 4/5 — Same 40-Pin Header)

The Pi Zero 2W uses the same 40-pin header layout as Pi 4/5. All GPIO BCM numbers are identical. [VERIFIED: wevolver.com Pi Zero 2W pinout guide]

**I2C bus (shared by all I2C sensors on same node):**
- SDA: GPIO2, Physical Pin 3
- SCL: GPIO3, Physical Pin 5
- Both have fixed 1.8kΩ pull-ups to 3.3V on the Pi itself
- I2C is enabled via `dtparam=i2c_arm=on` in `/boot/config.txt`

**1-Wire bus (DS18B20 temperature sensors):**
- Default 1-Wire GPIO: GPIO4, Physical Pin 7
- Enabled via `dtoverlay=w1-gpio` in `/boot/config.txt`
- Requires external 4.7kΩ pull-up resistor between DQ and 3.3V
- Multiple DS18B20 sensors can share this single pin

**I2C address map (garden zone node):**
| Device | I2C Address | Notes |
|--------|------------|-------|
| Adafruit STEMMA Soil Sensor | 0x36 (default) | Addresses 0x36–0x39 via AD0/AD1 solder jumpers |
| ADS1115 (pH ADC) | 0x48 (default) | Addresses 0x48–0x4B via ADDR pin; default = ADDR to GND |

With STEMMA at 0x36 and ADS1115 at 0x48, these addresses do NOT conflict. No I2C multiplexer needed on garden nodes. [VERIFIED: adafruit.com/product/4026 pinouts page, adafruit.com/product/1085]

**I2C address map (coop node):**
| Device | I2C Address | Notes |
|--------|------------|-------|
| ADS1115 (water level or pH) | 0x48 | Same as garden node |

HX711 load cell amplifier uses GPIO-bit-banged protocol (not I2C/SPI) — connects to any two GPIO pins. Standard library (hx711py or RPi.GPIO) handles bit-bang timing.

### Fritzing Diagram Creation

**Fritzing version:** 1.0.6 (December 2025, latest stable) [VERIFIED: GitHub fritzing/fritzing-app releases]

**Licensing:** Source code is GPL v3 (free to build from source). Official binaries at fritzing.org require a minimum €8 contribution. Either approach is acceptable. [VERIFIED: github.com/fritzing/fritzing-app]

**Workflow:**
1. Download Fritzing 1.0.6 from fritzing.org or build from source
2. Create breadboard view for each subsystem (not schematic view — breadboard is what non-engineers read)
3. Save `.fzz` file to `docs/hardware/fritzing/[name].fzz`
4. Export PNG: File → Export → As Image → PNG, 150 DPI minimum
5. Save PNG to `docs/hardware/fritzing/[name].png`
6. Reference PNG in subsystem Markdown doc

**Raspberry Pi part in Fritzing:** The Pi Zero 2W part is available in the Fritzing parts library. If not present in the default install, search the Fritzing parts repository (github.com/fritzing/fritzing-parts) — "Raspberry Pi Zero 2 W" was added in 2022. [ASSUMED — specific part availability in library version 1.0.6 not verified]

**Alternative to Fritzing for diagram creation:** If the author does not have a machine that can run Fritzing, Wokwi (wokwi.com) is a free browser-based circuit simulator that can export diagrams, but it cannot save `.fzz` format. For D-06 compliance, Fritzing is required. [ASSUMED — Wokwi export format compatibility with `.fzz` not verified]

---

## Sensor-to-Code Cross-Reference (Required for DOC-02)

The documentation must map every hardware connection to specific code constants, config variables, and MQTT topics. This table gives the planner the raw data:

### Garden Zone Node Cross-Reference

| Hardware | Connection | Code File | Constant/Variable | Current Value |
|----------|-----------|-----------|-------------------|---------------|
| Adafruit STEMMA Soil Sensor | I2C 0x36 | `edge/daemon/sensors.py` | MoisturePlaceholder (needs update) | TBD |
| ADS1115 pH ADC | I2C 0x48, channel A0 | `edge/daemon/sensors.py` | ADS1115PHDriver.i2c_address | 0x48 |
| DS18B20 temperature | 1-Wire GPIO4 | `edge/daemon/sensors.py` | DS18B20Driver | auto-detected via w1thermsensor |
| Irrigation solenoid relay | GPIO (TBD) | `edge/daemon/rules.py` | execute_action(IRRIGATION_SHUTOFF) | stub in Phase 1; wired Phase 2 |
| MQTT publish topic — moisture | MQTT | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/sensors/moisture` | e.g., `farm/zone-01/sensors/moisture` |
| MQTT publish topic — ph | MQTT | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/sensors/ph` | e.g., `farm/zone-01/sensors/ph` |
| MQTT publish topic — temperature | MQTT | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/sensors/temperature` | e.g., `farm/zone-01/sensors/temperature` |
| Hub IP (MQTT broker) | Network | `config/hub.env` | HUB_IP | 192.168.1.100 |
| MQTT port | Network | `config/hub.env` | MQTT_PORT | 1883 |
| Node MQTT username | MQTT auth | `hub/mosquitto/passwd` | node_id | zone-01 through zone-04 |

### Coop Node Cross-Reference

| Hardware | Connection | Code File | Constant/Variable | Current Value |
|----------|-----------|-----------|-------------------|---------------|
| HX711 feed load cell | GPIO bit-bang (2 pins) | `edge/daemon/sensors.py` | (stub — needs implementation) | TBD |
| HX711 nesting box load cell | GPIO bit-bang (2 pins) | `edge/daemon/sensors.py` | (stub — needs implementation) | TBD |
| Water level float switch | GPIO input (1 pin) | `edge/daemon/sensors.py` | (stub — needs implementation) | TBD |
| Linear actuator motor | GPIO → L298N H-bridge | `edge/daemon/rules.py` | execute_action(COOP_HARD_CLOSE) | stub in Phase 1 |
| Limit switch (open position) | GPIO input (NC) | `edge/daemon/main.py` | (stub — Phase 2 wired) | TBD GPIO |
| Limit switch (closed position) | GPIO input (NC) | `edge/daemon/main.py` | (stub — Phase 2 wired) | TBD GPIO |
| Coop door MQTT command topic | MQTT | `docs/mqtt-topic-schema.md` | `farm/coop/commands/coop_door` | action: "open" or "close" |
| Coop door MQTT ack topic | MQTT | `docs/mqtt-topic-schema.md` | `farm/coop/ack/{command_id}` | status: "confirmed" or "failed" |
| Feed weight MQTT topic | MQTT | `docs/mqtt-topic-schema.md` | `farm/coop/sensors/feed_weight` | grams |
| Water level MQTT topic | MQTT | `docs/mqtt-topic-schema.md` | `farm/coop/sensors/water_level` | percent or binary |
| Hub latitude/longitude (sunrise/sunset) | Config | `hub/bridge/coop_scheduler.py` | HUB_LATITUDE, HUB_LONGITUDE | 37.7749, -122.4194 (defaults) |

### Hub Cross-Reference

| Hardware | Connection | Code File | Variable | Value |
|----------|-----------|-----------|---------|-------|
| Hub IP address | Network | `config/hub.env` | HUB_IP | 192.168.1.100 |
| MQTT broker port | Network | `config/hub.env` | MQTT_PORT | 1883 |
| HTTPS port (Caddy) | Network | `config/hub.env` | HUB_HTTPS_PORT | 443 |
| TimescaleDB port | Network | `config/hub.env` | TIMESCALEDB_PORT | 5432 |
| SSD mount path for TimescaleDB data | OS | `config/hub.env` | SSD_MOUNT | ./data/timescaledb |
| MQTT bridge credentials | Auth | `hub/bridge/main.py` | MQTT_BRIDGE_USER | hub-bridge |

Note: The `MQTT_BRIDGE_PASS` in `config/hub.env` contains a credential that should be documented as "generated by `hub/mosquitto/generate-passwords.sh`" — do not expose the actual value in hardware docs. [VERIFIED: config/hub.env file contains this credential]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Moisture sensor reading | ADC-based analog resistive probe | Adafruit STEMMA Soil Sensor (capacitive I2C) | Capacitive sensors don't corrode in soil; I2C eliminates ADC; 4 selectable addresses eliminate need for multiplexer on 4-zone system |
| DS18B20 GPIO bit-banging | Custom 1-Wire protocol | `w1-therm` Linux kernel module + `w1thermsensor` Python library | Kernel module handles timing-critical 1-Wire protocol; library already integrated in `edge/daemon/sensors.py` |
| Load cell ADC | Discrete op-amp circuit | HX711 breakout module | HX711 is purpose-built 24-bit ADC for load cells; widely supported; hx711py Python library handles bit-bang timing |
| Motor H-bridge | Discrete transistors | L298N module | L298N handles the flyback diode protection, current sensing, and heat dissipation needed for 12V motor loads |
| Relay isolation | Direct GPIO-to-relay | Optocoupler relay board | Direct GPIO drive risks back-EMF damage to Pi; optocoupler boards are $6 and fully protect the Pi |
| Power conversion | Linear regulator (7805) | LM2596 buck converter | Linear regulators waste 60%+ of input power as heat at 12V→5V; buck converters are 85-95% efficient |

---

## Common Pitfalls

### Pitfall 1: Relay Active-Low Behavior
**What goes wrong:** Many relay boards are active-LOW — the relay CLOSES when GPIO is pulled LOW, not HIGH. On boot, the Pi's GPIO pins may float LOW momentarily, briefly closing the valve.
**Why it happens:** Optocoupler relay boards are commonly designed for active-low triggering to avoid boot-state relay activation, but the behavior surprises users.
**How to avoid:** Test relay behavior BEFORE connecting any valve or actuator: `gpio write [pin] 1` should have NO effect if active-low; `gpio write [pin] 0` should click relay. Document the active-high vs active-low behavior in each subsystem doc. The ROADMAP.md already flags this as a Phase 1 gate: "Relay board(s) procured and cold-boot relay state tested BEFORE connecting any valve or actuator."
**Warning signs:** Valve briefly opens on Pi boot. Test with relay board unconnected from valve first.

### Pitfall 2: I2C Pull-Up Conflicts
**What goes wrong:** Adding external I2C pull-up resistors when the Pi already has 1.8kΩ pull-ups, or when STEMMA modules add their own 10kΩ pull-ups. Multiple pull-ups cause bus instability.
**Why it happens:** Tutorials often recommend 4.7kΩ external pull-ups, but the Pi has internal pull-ups on GPIO2/3 and the STEMMA sensor adds 10kΩ to VIN.
**How to avoid:** Do not add external pull-up resistors to the I2C bus. The Pi's internal 1.8kΩ pull-ups are sufficient. The STEMMA sensor's 10kΩ is parallel to the 1.8kΩ (resulting in ~1.5kΩ effective pull-up) — acceptable. [VERIFIED: learn.adafruit.com STEMMA pinouts page]
**Warning signs:** I2C bus hangs, `i2cdetect -y 1` shows no devices or garbled addresses.

### Pitfall 3: DS18B20 Missing Pull-Up Resistor
**What goes wrong:** Temperature sensor doesn't appear in `/sys/bus/w1/devices/`, `w1thermsensor.NoSensorFoundError` in logs.
**Why it happens:** The 1-Wire protocol requires a pull-up resistor on the DQ line. Without it, the bus is floating and the sensor cannot communicate.
**How to avoid:** Always install a 4.7kΩ resistor between DQ (data) and VCC (3.3V). This single resistor is the most common missed component in DS18B20 wiring. The diagram must highlight it prominently. [VERIFIED: pimylifeup.com DS18B20 tutorial, Waveshare wiki]
**Warning signs:** No devices in `/sys/bus/w1/devices/`. The directory exists (kernel module loaded) but is empty.

### Pitfall 4: Solenoid Valve Polarity/NC Confusion
**What goes wrong:** Irrigation valve opens when power is lost (dangerous — floods the garden).
**Why it happens:** Normally-open (NO) valves are sometimes stocked alongside NC valves. They look identical. The label "NC" may not be visible on the body.
**How to avoid:** Order specifically from suppliers that clearly label NC (normally-closed). U.S. Solid's product pages and Amazon listings explicitly state NC. Verify by testing: with no power applied, try to push water through manually — NC valve should block flow. REQUIREMENTS.md IRRIG-03 mandates NC valves.
**Warning signs:** Any valve that passes water when unpowered is a NO valve and must be replaced.

### Pitfall 5: Pi Zero 2W GPIO 3.3V Current Limit
**What goes wrong:** Pi Zero 2W GPIO pins maximum 3.3V/16mA per pin, 50mA total for all GPIO. Connecting sensors that draw more than this will damage the Pi.
**Why it happens:** Sensors that power via 3.3V from the Pi GPIO power pins are fine (the 3.3V regulator on the Pi supplies 500mA+). But sensors powered directly from a GPIO DATA pin (not a dedicated power pin) will exceed limits.
**How to avoid:** Always power sensors from the dedicated 3.3V or 5V power pins (physical pin 1/17 for 3.3V, pin 2/4 for 5V), NOT from GPIO data pins. All sensors in the BOM are I2C or 1-Wire and follow this convention.
**Warning signs:** Pi reboots under load, GPIO voltage drops below 3V under measurement.

### Pitfall 6: 12V Solenoid Back-EMF
**What goes wrong:** The relay board is damaged or Pi behaves erratically when irrigation valves switch off.
**Why it happens:** Inductive loads (solenoid valves) generate a voltage spike when power is removed (back-EMF). The relay board must have flyback diode protection.
**How to avoid:** Use relay boards with onboard flyback diode protection — all optocoupler relay boards in the recommended BOM include this. Do NOT use bare relay modules without protection. Add a 1N4007 diode across solenoid terminals if using bare solenoid driver circuits.
**Warning signs:** Relay board gets warm, Pi USB power rail shows voltage dips on irrigation valve switching.

### Pitfall 7: Fritzing .fzz Source Not Committed
**What goes wrong:** Only PNG images are committed; the editable source is lost. Future contributors cannot update diagrams when hardware changes.
**Why it happens:** PNG is the visible output; `.fzz` is the source. Authors often commit only what they can see.
**How to avoid:** Per D-06, the `.fzz` files MUST be committed under `docs/hardware/fritzing/`. The planner should make `.fzz` commit an explicit task requirement, not optional.

### Pitfall 8: Budget Exceeds $500 Target
**What goes wrong:** The BOM total significantly exceeds the D-04 $500 target, especially with 2026 Raspberry Pi RAM pricing.
**Why it happens:** The Pi 5 8GB hub alone costs ~$175 (up from $80 originally); 4× Pi Zero 2W adds ~$68; sensors and actuators add ~$200+.
**How to avoid:** The planner must (a) calculate the realistic total in `bom.md`, (b) flag the gap explicitly to the user, and (c) include a "budget alternatives" section in `bom.md` with cost-saving options. Do not present a false $500 total.

---

## Code Examples

### Detecting I2C Devices on Raspberry Pi

```bash
# Source: Raspberry Pi documentation
# Run after wiring sensors, before starting the daemon
sudo i2cdetect -y 1
# Expected output for garden node:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 30: -- -- -- -- -- -- 36 -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
# 0x36 = Adafruit STEMMA soil sensor, 0x48 = ADS1115
```

### Detecting DS18B20 on 1-Wire

```bash
# Source: Raspberry Pi Documentation / Pi My Life Up
# Enable 1-Wire in /boot/config.txt first:
#   dtoverlay=w1-gpio
# Then reboot and verify:
ls /sys/bus/w1/devices/
# Expected: 28-xxxxxxxxxxxx (one entry per DS18B20)
cat /sys/bus/w1/devices/28-*/w1_slave
# Expected: ... YES\n... t=22500  (temperature in millidegrees C)
```

### Testing Relay Board Before Connecting Actuators

```python
# Source: general Raspberry Pi GPIO practice
# Run this BEFORE connecting any solenoid or motor to the relay
import RPi.GPIO as GPIO
import time

RELAY_PIN = 17  # BCM pin — adjust to actual assigned pin

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Test: write HIGH
GPIO.output(RELAY_PIN, GPIO.HIGH)
print("HIGH set — listen for relay click")
time.sleep(2)

# Test: write LOW
GPIO.output(RELAY_PIN, GPIO.LOW)
print("LOW set — listen for relay click")
time.sleep(2)

GPIO.cleanup()
# Document which level (HIGH or LOW) causes the relay to CLOSE
# This determines whether the board is active-HIGH or active-LOW
```

### Reading STEMMA Soil Sensor I2C Address

```python
# Source: Adafruit CircuitPython library pattern
# adafruit-circuitpython-seesaw required: pip install adafruit-circuitpython-seesaw
import board
import busio
from adafruit_seesaw.seesaw import Seesaw

i2c = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c, addr=0x36)  # default address; change to 0x37/0x38/0x39 for others

moisture = ss.moisture_read()  # Returns 200 (dry) to 2000 (wet)
temp_c = ss.get_temp()          # Temperature in Celsius
print(f"Moisture: {moisture}, Temp: {temp_c:.1f}°C")
```

### Smoke Test: Verify MQTT Publish from Edge Node

```bash
# Source: Mosquitto documentation
# On hub — subscribe to verify edge node is publishing
mosquitto_sub -h localhost -p 1883 \
  -u hub-bridge -P "[MQTT_BRIDGE_PASS from config/hub.env]" \
  -t "farm/zone-01/#" -v

# Expected output within 60 seconds of node boot:
# farm/zone-01/sensors/moisture {"zone_id": "zone-01", "sensor_type": "moisture", ...}
# farm/zone-01/sensors/ph {...}
# farm/zone-01/sensors/temperature {...}
# farm/zone-01/heartbeat {...}
```

---

## Smoke Test Procedures (Per Subsystem)

The planner should use these as the basis for the "Smoke Test" section in each subsystem doc:

### Hub Smoke Test
1. Connect Pi 5 8GB to monitor via HDMI, power via official PSU
2. Verify boot to login prompt (no kernel panics)
3. Confirm `docker compose up -d` starts all services: `docker compose ps` shows all green
4. Confirm HTTPS dashboard accessible at `https://[HUB_IP]` from another device on LAN
5. Run `mosquitto_pub -h localhost -t farm/test -m "hello"` — no error means broker running

### Garden Node Smoke Test
1. Power Pi Zero 2W via USB, confirm boot
2. Confirm I2C devices: `sudo i2cdetect -y 1` shows 0x36 and 0x48
3. Confirm 1-Wire: `ls /sys/bus/w1/devices/` shows DS18B20 device
4. Insert soil sensor probe into a glass of water — moisture reading should increase
5. Start edge daemon: confirm MQTT messages appear on hub subscriber (see example above)
6. Confirm TimescaleDB has rows: `SELECT count(*) FROM sensor_readings WHERE zone_id='zone-01';`

### Irrigation Relay Smoke Test
1. Connect relay board to Pi GPIO WITHOUT valve attached
2. Run relay test script (example above): confirm both HIGH and LOW cause relay click
3. Document which logic level closes relay (active-high or active-low)
4. Connect valve to relay COM/NC terminals (unpowered)
5. Power solenoid through relay: confirm valve click (do NOT connect to water yet)
6. Connect water supply: confirm valve opens and closes cleanly

### Coop Node Smoke Test
1. Verify actuator moves: `python test_actuator.py` (to be written in Phase 6 plan task)
2. Confirm linear actuator stops at hardware end-stop without motor damage
3. Confirm limit switches trigger GPIO input: `gpio read [pin]` changes 0→1 when door reaches position
4. Verify load cell reading: tare to zero, place known weight (e.g., 500g), confirm reading ±5%
5. Confirm coop MQTT topics appear on hub: `feed_weight`, `water_level`, `coop/ack/`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Adafruit STEMMA Soil Sensor part 4026 needs adafruit-circuitpython-seesaw driver (not the ads1x15 library) | Code Examples | Planner writes wrong pip install; 30-minute fix |
| A2 | Two separate limit switches required for COOP-03 (external GPIO confirmation beyond built-in motor limit switches) | Coop Node Hardware | System built without external limit switches; COOP-03 requirement not met |
| A3 | DC-DC buck converter (12V→5V) approach is appropriate for outdoor node power distribution | Power Distribution | Reliability issue if buck converters chosen are low quality; single-cable approach may complicate troubleshooting |
| A4 | Budget significantly exceeds $500 D-04 target (~$742 estimated) | Budget Analysis | If prices change or alternatives are found, actual total may be lower |
| A5 | Fritzing Pi Zero 2W part available in library 1.0.6 | Fritzing Workflow | Author spends time finding/importing part from fritzing-parts GitHub repo |
| A6 | Coop node Pi 5 4GB is appropriate vs Pi 4 | Compute Nodes | ONNX inference might need more RAM; if 4GB is insufficient, upgrade to 8GB adding ~$115 |
| A7 | L298N H-bridge adequate for ECO-WORTHY linear actuator current draw | Coop Node | L298N max 2A continuous; verify actuator stall current doesn't exceed this |
| A8 | One 4-channel relay board per garden zone node sufficient (4 channels: 3 for future, 1 for irrigation valve) | Irrigation | If 2+ valves needed per zone, need additional relay board |

---

## Open Questions

1. **Exact moisture sensor driver integration**
   - What we know: `edge/daemon/sensors.py` has `MoisturePlaceholder` with comment "sensor model TBD per D-01 research spike"
   - What's unclear: Phase 6 documents hardware, but the STEMMA sensor needs a real Python driver. Does Phase 6 include writing the `StemmaSoilSensor` driver in `sensors.py`, or is that outside scope ("pure documentation only")?
   - Recommendation: Phase 6 is documented as "no application code changes." The planner should note in `garden-node.md` that the `MoisturePlaceholder` must be replaced before the node can run. Consider whether Phase 6 or Phase 7 (tutorial) includes this gap closure.

2. **GPIO pin assignments for relay control**
   - What we know: The relay GPIO pins are stubs in Phase 1 code (`execute_action` logs only)
   - What's unclear: No specific GPIO pins were assigned for relay control in any existing code
   - Recommendation: The planner should assign specific GPIO pins in the wiring diagrams AND update `edge/daemon/sensors.py` (or a constants file) with named constants for each GPIO. Recommend: GPIO17=relay 1 (valve), GPIO27=relay 2, GPIO22=actuator direction A, GPIO23=actuator direction B, GPIO24=actuator enable.

3. **Coop Pi model — Pi 4 vs Pi 5**
   - What we know: D-02 says "Raspberry Pi 4 or 5"; current pricing favors Pi 5 4GB (~$60) over Pi 4 4GB (~$55)
   - What's unclear: Does ONNX inference (Phase 4) have specific memory requirements for the coop domain?
   - Recommendation: Use Pi 5 4GB for coop — $5 more than Pi 4 4GB, significantly better CPU for ONNX inference, same OS image.

4. **Budget gap resolution**
   - What we know: Estimated BOM total ~$742, D-04 target $500
   - What's unclear: Whether user accepts the overage or wants cost-cutting alternatives
   - Recommendation: The planner should write `bom.md` with the full accurate total AND a "budget alternatives" appendix. Let the user decide. Do not downscope silently.

---

## Environment Availability

Step 2.6: This phase is documentation-only with no runtime execution. However, Fritzing must be available on the author's machine to create diagrams.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Fritzing | D-05, D-06, D-07 — wiring diagrams | Not installed (not found on machine) | — | Build from source (GPL v3 free) or pay €8 for official binary; no other fallback for .fzz format |
| `i2cdetect` utility | Smoke test verification | N/A (runs on Pi, not dev machine) | — | Adafruit CircuitPython scanner |
| Git (for committing .fzz + PNG) | D-06, D-07 | Present (project is git repo) | — | — |

**Missing dependencies:**
- Fritzing not installed on dev machine. The planner must include a task: "Install Fritzing 1.0.6 — download from fritzing.org (€8 minimum contribution) or build from source per github.com/fritzing/fritzing-app." This is a prerequisite gate for all diagram tasks.

---

## Validation Architecture

Phase 6 is a documentation-only phase. There is no application code and no automated test suite to run. The validation model is human verification:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | Shopping list covers all components with part numbers, quantities, prices, links, and total | Manual review | N/A — human reads bom.md | ❌ Wave 0: create bom.md |
| DOC-01 | Total cost summary present in bom.md | Manual review | N/A | ❌ Wave 0: create bom.md |
| DOC-02 | Wiring diagrams exist for every connection type | Manual review | N/A | ❌ Wave 0: create fritzing/ dir and diagrams |
| DOC-02 | Each diagram has smoke test procedure | Manual review | N/A | ❌ Wave 0: write subsystem docs |
| DOC-02 | Docs cross-reference codebase | Manual review | N/A | ❌ Wave 0: write code cross-reference tables |

**Phase gate:** Human sign-off required. Before closing Phase 6, the author should:
1. Follow `bom.md` to add one component to a cart and confirm the link works
2. Follow `garden-node.md` from scratch (no prior knowledge) and verify the smoke test passes on actual hardware

---

## Security Domain

Phase 6 is hardware documentation only. No application code is written or modified. Security domain is not applicable.

The hardware documentation itself should note:
- MQTT credentials are per-node; do not share credentials between nodes (already enforced by `hub/mosquitto/passwd` design)
- The `config/hub.env` file contains credentials; reference it as "see hub.env, never paste credentials into documentation"
- Physical access to the hub SD card allows reading `hub.env` — this is accepted risk for a local-only, home-network system

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Resistive soil moisture sensors | Capacitive sensors (STEMMA I2C) | ~2018 | No corrosion in soil; longer lifespan |
| Schematic-only wiring docs | Fritzing breadboard-style diagrams | ~2012 | Non-engineers can follow without training |
| One cable per sensor | STEMMA/Qwiic JST daisy-chain | ~2018 | Single cable with standardized 4-pin connector reduces wiring errors |
| USB-powered Raspberry Pi edge nodes | Buck converter from 12V rail | Ongoing practice | Single outdoor cable run simplifies installation |
| Raspberry Pi 4 as default hub | Raspberry Pi 5 (2023+) | 2023 | Significantly faster; NVMe HAT available; required for Docker Compose performance |

**Deprecated/outdated:**
- Fritzing 0.9.3b (2016): outdated, missing many modern parts including Pi Zero 2W; use 1.0.6
- `RPi.GPIO` library: deprecated in Python 3.12+; Pi 5 uses different GPIO subsystem; use `gpiozero` or `lgpio` for new code

---

## Sources

### Primary (HIGH confidence)
- [adafruit.com/product/4026](https://www.adafruit.com/product/4026) — STEMMA soil sensor price ($7.50), I2C
- [learn.adafruit.com/adafruit-stemma-soil-sensor-i2c-capacitive-moisture-sensor/pinouts](https://learn.adafruit.com/adafruit-stemma-soil-sensor-i2c-capacitive-moisture-sensor/pinouts) — I2C address 0x36, address jumpers AD0/AD1, pinout
- [adafruit.com/product/1085](https://www.adafruit.com/product/1085) — ADS1115 price ($14.95), I2C addresses 0x48–0x4B
- [pishop.us/product/raspberry-pi-zero-2-w](https://www.pishop.us/product/raspberry-pi-zero-2-w/) — Pi Zero 2W price ($17.25)
- [pishop.us/product/raspberry-pi-5-8gb](https://www.pishop.us/product/raspberry-pi-5-8gb/) — Pi 5 8GB price ($175.00)
- [github.com/fritzing/fritzing-app](https://github.com/fritzing/fritzing-app) — GPL v3 license, build from source
- [pinout.xyz/pinout/i2c](https://pinout.xyz/pinout/i2c) — GPIO2/GPIO3 I2C pins, 1.8kΩ pull-ups
- `edge/daemon/sensors.py` — existing ADS1115PHDriver (0x48), DS18B20Driver, MoisturePlaceholder
- `docs/mqtt-topic-schema.md` — locked topic schema, node credentials, actuator command format
- `config/hub.env` — HUB_IP, MQTT_PORT, TIMESCALEDB_PORT, SSD_MOUNT

### Secondary (MEDIUM confidence)
- [Tom's Hardware — Raspberry Pi 5 price hike April 2026](https://www.tomshardware.com/raspberry-pi/raspberry-pi-5-price-increases-drastically-as-ai-shortage-bites-16gb-version-now-usd205-second-price-increase-in-three-months-over-70-percent-more-expensive-than-original-msrp) — RAM crisis pricing context
- [ussolid.com — 3/4" NC solenoid valve](https://ussolid.com/products/3-4-solenoid-valve-brass-12v-dc-normally-closed-with-viton-seal-html) — valve type and NC spec
- [wevolver.com — Pi Zero 2W pinout](https://www.wevolver.com/article/raspberry-pi-zero-2-w-pinout-comprehensive-guide-for-engineers) — 40-pin header confirmed same as Pi 4
- [pimylifeup.com DS18B20](https://pimylifeup.com/raspberry-pi-temperature-sensor/) — 4.7kΩ pull-up requirement
- [Fritzing 1.0.6 release](https://arduinofactory.fr/en/download-fritzing-for-free/) — version confirmed December 2025

### Tertiary (LOW confidence)
- Budget totals: estimated from individual component prices researched separately; actual cart total not verified
- Coop node L298N motor driver suitability for ECO-WORTHY linear actuator: not load-tested

---

## Metadata

**Confidence breakdown:**
- Component identification: HIGH — all sensors already locked in Phase 1 decisions and codebase; STEMMA recommendation confirmed via Adafruit docs
- Pricing: MEDIUM — individual prices verified at specific retailers but volatile; 2026 RAM shortage affects Pi prices significantly
- GPIO pinout: HIGH — verified via pinout.xyz and Raspberry Pi official docs, confirmed against existing sensor drivers in codebase
- Budget total: LOW — summed from individual prices; not a single-cart verified total; known to exceed $500 target
- Fritzing workflow: HIGH — tool confirmed GPL v3, version 1.0.6 latest stable, platform support confirmed

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (30 days) — Raspberry Pi prices particularly volatile; re-verify before committing BOM totals to documentation
