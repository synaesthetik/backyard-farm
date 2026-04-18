# Backyard Farm Platform — Master Bill of Materials

<!-- DOC-01 -->

## Before You Buy

This document lists every component needed to build the complete backyard farm platform — four garden zone edge nodes, one coop edge node, one hub, irrigation solenoids, power supplies, enclosures, and wiring. Read this entire document before placing any orders, because some components require configuration choices (for example, selecting normally-closed solenoid valves) that are explained in context. Quantities and prices are organized so you can fill a single shopping cart with everything. Prices are estimates as of April 2026 and may vary; always check current prices before ordering.

## Budget Summary

> **Estimated total: ~$742**
>
> The original budget target was $500. Current Raspberry Pi pricing (2026 RAM shortage)
> has pushed the hub alone to ~$175. See "Budget Alternatives" at the bottom of this
> page for ways to reduce cost.

| Subsystem | Estimated Cost |
|-----------|---------------|
| Hub (Pi 5 8GB + SSD + HAT + PSU) | ~$232 |
| 4× Garden zone nodes (Pi Zero 2W + SD + sensors) | ~$220 |
| 1× Coop edge node (Pi 5 4GB + SD + sensors + actuator) | ~$130 |
| Irrigation (solenoid valves + relay + fittings) | ~$60 |
| Power + enclosures + wiring | ~$100 |
| **Total** | **~$742** |

Note: Prices are estimates as of April 2026. Raspberry Pi availability and pricing fluctuates. Always check current prices before ordering.

---

## Section 1: Hub

The hub is the central computer that runs the database, MQTT broker, API server, and dashboard. It runs 24/7 and handles all data aggregation and AI inference.

> **Note:** The hub runs 24/7. Use the official PSU and an SSD — SD cards wear out in TimescaleDB write patterns within months.

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purchase Link | Fallback Spec |
|-----------|-----------|-----------|-----|----------|---------------|---------------|
| Raspberry Pi 5 8GB | SC1112 | ~$175 | 1 | ~$175 | [raspberrypi.com/products/raspberry-pi-5/](https://www.raspberrypi.com/products/raspberry-pi-5/) | Any ARM64 single-board computer with 8GB+ RAM running Debian-based Linux |
| Raspberry Pi M.2 HAT+ | SC1166 | ~$12 | 1 | ~$12 | [raspberrypi.com/products/m2-hat-plus/](https://www.raspberrypi.com/products/m2-hat-plus/) | Any PCIe NVMe adapter compatible with Pi 5 |
| M.2 NVMe SSD 256GB | (any brand) | ~$30 | 1 | ~$30 | [search Amazon: "M.2 2242 NVMe SSD 256GB"](https://www.amazon.com/s?k=M.2+2242+NVMe+SSD+256GB) | Any M.2 2242 or 2280 NVMe SSD, 256GB minimum; SATA M.2 also works |
| Raspberry Pi 5 Official PSU 5V/5A | SC1155 | $12 | 1 | $12 | [raspberrypi.com/products/27w-power-supply/](https://www.raspberrypi.com/products/27w-power-supply/) | Any USB-C power supply rated 5V/5A (27W); do not use phone chargers |

**Hub subtotal: ~$229**

---

## Section 2: Garden Zone Edge Nodes (×4)

> **Note:** You need 4 identical nodes, one per garden zone. Buy 4 of everything in this section (the Qty column shows the total across all 4 nodes).

Each garden zone node is a small computer that reads soil sensors and publishes readings to the hub over WiFi. The Pi Zero 2W is chosen for its low cost and built-in WiFi; it runs full Linux and Python.

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purchase Link | Fallback Spec |
|-----------|-----------|-----------|-----|----------|---------------|---------------|
| Raspberry Pi Zero 2W | SC1146 | ~$17 | 4 | ~$68 | [raspberrypi.com/products/raspberry-pi-zero-2-w/](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) | Any ARMv8 SBC with 40-pin GPIO, WiFi, running Linux — must support Python 3.10+ |
| Samsung Pro Endurance microSD 32GB (A2) | MB-MJ32KA | ~$12 | 4 | ~$48 | [amazon.com/dp/B09W9XYQCQ](https://www.amazon.com/dp/B09W9XYQCQ) | Any A2-rated endurance microSD, 32GB minimum; avoid generic unrated cards |
| Adafruit STEMMA Soil Sensor | ID 4026 | $7.50 | 4 | $30 | [adafruit.com/product/4026](https://www.adafruit.com/product/4026) | Any capacitive soil moisture sensor with I2C interface, 3.3V, selectable address 0x36–0x39 |
| Adafruit ADS1115 16-bit ADC breakout | ID 1085 | $14.95 | 4 | ~$60 | [adafruit.com/product/1085](https://www.adafruit.com/product/1085) | Any ADS1115-based I2C ADC breakout, 4-channel, 16-bit, 3.3V compatible |
| DS18B20 waterproof temperature probe | Adafruit ID 381 | ~$4.00 | 4 | $16 | [adafruit.com/product/381](https://www.adafruit.com/product/381) | Any DS18B20-based waterproof probe with 1-Wire interface, 3.3V compatible |
| 4.7kΩ resistor (1/4W) | generic | ~$0.10 | 4 | ~$0.40 | [adafruit.com/product/2781 (resistor kit)](https://www.adafruit.com/product/2781) | Any 4.7kΩ ±5% resistor — required for DS18B20 1-Wire pull-up |
| DFRobot Analog pH Meter V2 | SEN0161-V2 | ~$10 | 4 | $40 | [dfrobot.com/product-1782.html](https://www.dfrobot.com/product-1782.html) | Any analog pH probe with BNC connector output, 0–14 pH range; requires ADS1115 for ADC |
| JST PH 2mm 4-pin cable (100mm) | generic | ~$0.50 | 4 | $2 | [adafruit.com/product/3955](https://www.adafruit.com/product/3955) | Any JST PH 2mm 4-pin cable — matches STEMMA connector |
| Jumper wire kit | generic | ~$5 | 1 | $5 | [amazon.com: search "jumper wire kit assortment"](https://www.amazon.com/s?k=jumper+wire+kit+assortment) | Standard Dupont male-to-female and male-to-male jumper wires for GPIO connections |

**Garden zone nodes subtotal: ~$270 for 4 nodes**

---

## Section 3: Coop Edge Node (×1)

The coop node runs on a more powerful Raspberry Pi 5 because it handles ONNX ML inference for behavioral anomaly detection, controls the automatic door actuator, and reads more sensors than a garden node.

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purchase Link | Fallback Spec |
|-----------|-----------|-----------|-----|----------|---------------|---------------|
| Raspberry Pi 5 4GB | SC1112 | ~$60 | 1 | ~$60 | [raspberrypi.com/products/raspberry-pi-5/](https://www.raspberrypi.com/products/raspberry-pi-5/) | Raspberry Pi 4B 2GB (~$35) also works; ONNX inference may be slower |
| Samsung Pro Endurance microSD 32GB (A2) | MB-MJ32KA | ~$12 | 1 | ~$12 | [amazon.com/dp/B09W9XYQCQ](https://www.amazon.com/dp/B09W9XYQCQ) | Same as garden nodes |
| ECO-WORTHY 12V DC Linear Actuator | B088D7N85K | ~$35 | 1 | ~$35 | [amazon.com/dp/B088D7N85K](https://www.amazon.com/dp/B088D7N85K) | Any 12V DC linear actuator with internal limit switches, 100–150mm stroke, ≥35N force |
| Roller limit switch (NO type) | generic | ~$1.50 | 2 | $3 | [amazon.com: search "roller limit switch NO"](https://www.amazon.com/s?k=roller+limit+switch+NO+normally+open) | Any roller-type lever limit switch, normally-open, 12V–250V rated, panel-mount |
| L298N dual H-bridge motor driver | generic | ~$3 | 1 | ~$3 | [amazon.com: search "L298N motor driver module"](https://www.amazon.com/s?k=L298N+motor+driver+module) | Any L298N-based H-bridge module with enable/direction pins; must handle 12V/2A |
| HX711 + 5kg load cell kit | generic | ~$10 | 2 | ~$20 | [amazon.com: search "HX711 5kg load cell kit"](https://www.amazon.com/s?k=HX711+5kg+load+cell+kit) | Any HX711-based 24-bit ADC + single-point load cell rated ≥5kg, 5V excitation |
| Water level float switch | generic | ~$5 | 1 | ~$5 | [amazon.com: search "float switch water level"](https://www.amazon.com/s?k=float+switch+water+level) | Any vertical or horizontal float switch, NC or NO (document which), 12V or 5V signal compatible |
| DS18B20 waterproof temperature probe | Adafruit ID 381 | ~$4 | 1 | ~$4 | [adafruit.com/product/381](https://www.adafruit.com/product/381) | Same as garden nodes |
| 4.7kΩ resistor | generic | ~$0.10 | 1 | ~$0.10 | Same as garden nodes | Same as garden nodes |
| 4-channel optocoupler relay board | generic | ~$6 | 1 | ~$6 | [amazon.com: search "4 channel relay module optocoupler 5V"](https://www.amazon.com/s?k=4+channel+relay+module+optocoupler+5V) | Any 4-channel optocoupler relay board, 5V trigger, active-HIGH or active-LOW (document which) — any load cell fallback: any 5kg single-point load cell compatible with HX711 24-bit ADC, 5V excitation voltage |

**Coop node subtotal: ~$148**

---

## Section 4: Irrigation

> **SAFETY REQUIREMENT:** All irrigation solenoid valves MUST be normally-closed (NC) — the valve should block water when no power is applied. This is a safety requirement: if the system loses power, fields should not flood. This corresponds to IRRIG-03 in the software requirements. Confirm NC (normally-closed) before purchasing any solenoid valve.

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purchase Link | Fallback Spec |
|-----------|-----------|-----------|-----|----------|---------------|---------------|
| U.S. Solid 3/4" NC solenoid valve 12V DC | USS-SV series | ~$12 | 4 | $48 | [amazon.com: search "US Solid 3/4 solenoid valve normally closed 12V"](https://www.amazon.com/s?k=US+Solid+3%2F4+solenoid+valve+normally+closed+12V) | Any 3/4" NPT normally-closed solenoid valve, 12V DC coil, Viton seal; confirm NC before buying |
| 4-channel optocoupler relay board | generic | ~$6 | 1 | ~$6 | [amazon.com: search "4 channel relay module optocoupler 5V"](https://www.amazon.com/s?k=4+channel+relay+module+optocoupler+5V) | Any 4-channel optocoupler relay board, 5V trigger, supports both active-HIGH and active-LOW triggering, with flyback diode protection |
| 3/4" garden hose Y-splitter | generic | ~$8 | 1 | ~$8 | [amazon.com: search "3/4 garden hose splitter"](https://www.amazon.com/s?k=3%2F4+garden+hose+splitter) | Any 3/4" BSP or NPT Y-splitter with individual shutoffs; number of outputs = number of zones |
| 3/4" hose-to-NPT adapter | generic | ~$3 | 4 | $12 | [amazon.com: search "3/4 hose to NPT adapter"](https://www.amazon.com/s?k=3%2F4+hose+to+NPT+adapter) | Any 3/4" female hose × 3/4" male NPT adapter — connects hose supply to solenoid inlet |

**Irrigation subtotal: ~$74**

---

## Section 5: Power, Enclosures, and Wiring

This section covers everything needed to power the system outdoors and protect it from weather. All outdoor nodes use IP65-rated enclosures to keep out rain and moisture.

| Component | Model/SKU | Unit Price | Qty | Subtotal | Purchase Link | Fallback Spec |
|-----------|-----------|-----------|-----|----------|---------------|---------------|
| 12V 5A IP65 waterproof DC power supply | generic | ~$15 | 5 | ~$75 | [amazon.com: search "12V 5A power supply IP65 waterproof"](https://www.amazon.com/s?k=12V+5A+power+supply+IP65+waterproof) | Any IP65-rated 12V DC power supply, 5A minimum; 12V output powers solenoids and buck converters |
| Raspberry Pi 5 Official PSU 5V/5A | SC1155 | $12 | 2 | $24 | [raspberrypi.com/products/27w-power-supply/](https://www.raspberrypi.com/products/27w-power-supply/) | Hub and coop node dedicated power; same as Section 1 |
| DC-DC buck converter LM2596 12V→5V | generic | ~$3 | 4 | ~$12 | [amazon.com: search "LM2596 DC-DC buck converter module"](https://www.amazon.com/s?k=LM2596+DC-DC+buck+converter+module) | Any LM2596-based step-down module, 12V input, 5V/3A output; allows powering Pi Zero from 12V rail |
| IP65 ABS project enclosure ~150×100×70mm | generic | ~$8 | 6 | ~$48 | [amazon.com: search "IP65 ABS project box 150x100x70"](https://www.amazon.com/s?k=IP65+ABS+project+box+150x100x70) | Any IP65-rated plastic enclosure, approximately 150×100×70mm; one per outdoor node |
| Cable gland PG7 (for 3–6.5mm cable) | generic 10-pack | ~$5 | 1 | ~$5 | [amazon.com: search "PG7 cable gland 10 pack"](https://www.amazon.com/s?k=PG7+cable+gland+10+pack) | Any PG7 nylon cable glands; provides waterproof cable entry through enclosure |
| 18AWG stranded wire assortment (red/black + colors) | generic | ~$15 | 1 | ~$15 | [amazon.com: search "18AWG stranded wire kit"](https://www.amazon.com/s?k=18AWG+stranded+wire+kit) | 18AWG for 12V power runs; rated ≥300V; stranded is more flexible than solid |
| 22AWG Dupont jumper wire assortment | generic | ~$8 | 1 | ~$8 | [amazon.com: search "22AWG dupont jumper wire kit"](https://www.amazon.com/s?k=22AWG+dupont+jumper+wire+kit) | For GPIO and low-current signal connections on breadboard and pin headers |
| Heat shrink tubing assortment | generic | ~$5 | 1 | ~$5 | [amazon.com: search "heat shrink tubing assortment"](https://www.amazon.com/s?k=heat+shrink+tubing+assortment) | Multiple diameters; use for all exposed wire connections |
| Wago 221-412 or equivalent wire lever connectors | generic 20-pack | ~$10 | 1 | ~$10 | [amazon.com: search "Wago 221 lever connectors 2-wire"](https://www.amazon.com/s?k=Wago+221+lever+connectors+2-wire) | For splicing and joining power wire runs without soldering |

**Power + enclosures subtotal: ~$202**

---

## Budget Alternatives

If the ~$742 total is too high, here are options to reduce cost:

| Option | Savings | Tradeoff |
|--------|---------|----------|
| Use Raspberry Pi 4B 2GB for coop node instead of Pi 5 4GB | ~$25 | Slower ONNX inference; may not keep up with real-time load cell processing |
| Share one 12V power supply across 2–3 nodes instead of one per node | ~$30–45 | Longer wiring runs; slightly more complex |
| Stage procurement: buy hub + 1 garden node first (~$330 upfront) | ~$412 upfront | Remaining zones added later; system works with fewer zones |
| Source sensors from AliExpress | 30–50% sensor cost | 2–4 week shipping; variable quality; no Adafruit support |
| Use Pi Zero 2W for coop node if ONNX inference is not needed immediately | ~$43 | Cannot run ONNX models on coop node; hub handles inference |

---

## Component Quick-Reference Card

Use this compact list to copy and paste into an online order or shopping cart. All quantities are totals for the complete system.

| Item | Qty | Approx. Cost |
|------|-----|--------------|
| Raspberry Pi 5 8GB | 1 | $175 |
| Raspberry Pi 5 4GB | 1 | $60 |
| Raspberry Pi Zero 2W | 4 | $68 |
| Raspberry Pi M.2 HAT+ | 1 | $12 |
| M.2 NVMe SSD 256GB | 1 | $30 |
| Raspberry Pi 5 PSU (5V/5A) | 2 | $24 |
| Samsung Pro Endurance microSD 32GB | 5 | $60 |
| Adafruit STEMMA Soil Sensor (ID 4026) | 4 | $30 |
| Adafruit ADS1115 ADC breakout (ID 1085) | 4 | $60 |
| DS18B20 waterproof probe (Adafruit ID 381) | 5 | $20 |
| 4.7kΩ resistor (1/4W) | 5 | $0.50 |
| DFRobot pH Meter V2 (SEN0161-V2) | 4 | $40 |
| ECO-WORTHY 12V linear actuator (B088D7N85K) | 1 | $35 |
| Roller limit switch (NO type) | 2 | $3 |
| L298N motor driver module | 1 | $3 |
| HX711 + 5kg load cell kit | 2 | $20 |
| Water level float switch | 1 | $5 |
| 4-channel optocoupler relay board | 2 | $12 |
| U.S. Solid 3/4" NC solenoid valve 12V | 4 | $48 |
| 3/4" Y-splitter | 1 | $8 |
| 3/4" hose-to-NPT adapter | 4 | $12 |
| 12V 5A IP65 power supply | 5 | $75 |
| LM2596 DC-DC buck converter | 4 | $12 |
| IP65 project enclosure (~150×100×70mm) | 6 | $48 |
| PG7 cable gland (10-pack) | 1 | $5 |
| 18AWG stranded wire assortment | 1 | $15 |
| 22AWG Dupont wire assortment | 1 | $8 |
| JST PH 2mm 4-pin cable (100mm) | 4 | $2 |
| Heat shrink tubing assortment | 1 | $5 |
| Wago 221 lever connectors (20-pack) | 1 | $10 |
| Jumper wire kit | 1 | $5 |
| **Estimated Total** | | **~$742** |

---

## Wire Color Convention

Used consistently throughout all wiring diagrams for this system:

| Color | Function |
|-------|---------|
| Red | DC positive power (3.3V or 5V logic rails) |
| Orange | 12V DC power |
| Black | Ground / DC negative |
| Blue | I2C SDA |
| Yellow | I2C SCL |
| Green | GPIO signal / relay control |
| White | 1-Wire data (DS18B20) |
| Gray | Relay COM terminal |
| Purple | Relay NC (normally-closed) terminal |

---

*This document covers DOC-01. See also: [hub.md](hub.md) · [garden-node.md](garden-node.md) · [coop-node.md](coop-node.md) · [irrigation.md](irrigation.md) · [power.md](power.md)*
