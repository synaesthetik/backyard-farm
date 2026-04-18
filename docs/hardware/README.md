# Backyard Farm Platform — Hardware Documentation

This directory contains everything needed to build the complete backyard farm platform
from scratch. Follow these documents in order:

## Build Order

1. **[Master BOM](bom.md)** — Buy everything first. Read this before ordering.
2. **[Power](power.md)** — Set up power distribution before connecting anything.
3. **[Hub](hub.md)** — Assemble and configure the hub Raspberry Pi.
4. **[Garden Node](garden-node.md)** — Build one garden zone node (template for all 4 zones).
5. **[Coop Node](coop-node.md)** — Assemble the coop edge node with actuator and sensors.
6. **[Irrigation](irrigation.md)** — Wire solenoid valves and relay board.

## Directory Contents

| File | Purpose |
|------|---------|
| [bom.md](bom.md) | Master bill of materials — all components, prices, purchase links |
| [hub.md](hub.md) | Hub Raspberry Pi 5 assembly, SSD setup, Docker Compose |
| [garden-node.md](garden-node.md) | Garden zone edge node — soil moisture, pH, temperature sensors |
| [coop-node.md](coop-node.md) | Coop edge node — linear actuator, limit switches, load cell |
| [irrigation.md](irrigation.md) | Solenoid valve wiring and relay board |
| [power.md](power.md) | 12V power distribution, buck converters, weatherproofing |
| [fritzing/](fritzing/) | Fritzing `.fzz` source files and PNG diagram exports |

## Standard Document Structure

Every subsystem document in this directory follows the same pattern:

1. **Parts Needed** — Which BOM components this subsystem uses (with links)
2. **Overview Diagram** — Fritzing breadboard-style wiring diagram
3. **Wiring Table** — Every connection listed: From | To | Wire Color | Notes
4. **GPIO Pin Assignment Table** — BCM number, physical pin, function, connected-to
5. **Config File Cross-Reference** — Maps each hardware connection to its config constant in the codebase
6. **Smoke Test** — Step-by-step power-on verification before connecting the next subsystem
7. **Common Mistakes** — The 3-5 most common wiring errors for this subsystem

## Wire Color Convention

All diagrams in this documentation use the following wire color conventions:

| Color | Function |
|-------|---------|
| Red | DC positive power (3.3V or 5V logic power rails) |
| Orange | 12V DC power |
| Black | Ground / DC negative |
| Blue | I2C SDA (data) |
| Yellow | I2C SCL (clock) |
| Green | GPIO signal or relay control |
| White | 1-Wire data (DS18B20 temperature sensors) |
| Gray | Relay COM (common) terminal |
| Purple | Relay NC (normally-closed) terminal |

## Creating and Updating Fritzing Diagrams

All wiring diagrams in this documentation were created with [Fritzing](https://fritzing.org) 1.0.6
(December 2025 latest stable release). The `.fzz` source files are committed under `docs/hardware/fritzing/`
so anyone can open and edit them.

### Installing Fritzing

1. Download from [fritzing.org](https://fritzing.org) — requires a minimum €8 contribution for pre-built binaries
2. Alternatively, build from source (GPL v3): [github.com/fritzing/fritzing-app](https://github.com/fritzing/fritzing-app)
3. If the Raspberry Pi Zero 2W part is missing from the default library, download it from:
   [github.com/fritzing/fritzing-parts](https://github.com/fritzing/fritzing-parts)

### Workflow for Creating/Updating a Diagram

1. Open the `.fzz` source file in Fritzing: `docs/hardware/fritzing/[name].fzz`
2. Switch to **Breadboard view** (not Schematic or PCB view — breadboard view is what readers expect)
3. Make your changes
4. Save the `.fzz` file: **File → Save**
5. Export as PNG: **File → Export → As Image → PNG**
   - Set resolution to 150 DPI minimum
   - Save to `docs/hardware/fritzing/[name].png`
6. Commit both the `.fzz` and `.png` files to git

> **Important:** Always commit the `.fzz` source file alongside the PNG. If only the PNG is committed,
> future contributors cannot edit the diagram when hardware changes.

### Current Diagram Status

| Diagram | .fzz Source | PNG Exported | Subsystem Doc |
|---------|------------|--------------|---------------|
| garden-node | [garden-node.fzz](fritzing/garden-node.fzz) | [garden-node.png](fritzing/garden-node.png) | [garden-node.md](garden-node.md) |
| coop-node | [coop-node.fzz](fritzing/coop-node.fzz) | [coop-node.png](fritzing/coop-node.png) | [coop-node.md](coop-node.md) |
| irrigation-relay | [irrigation-relay.fzz](fritzing/irrigation-relay.fzz) | [irrigation-relay.png](fritzing/irrigation-relay.png) | [irrigation.md](irrigation.md) |
| power-distribution | [power-distribution.fzz](fritzing/power-distribution.fzz) | [power-distribution.png](fritzing/power-distribution.png) | [power.md](power.md) |

> **Note for builders:** The Fritzing diagrams require the author to create them using the Fritzing
> application. The `.fzz` placeholder files in the `fritzing/` directory are tracked in git as
> future diagram locations. Until the author creates the actual diagrams, the wiring tables in
> each subsystem document provide the complete connection information. The diagrams are visual
> supplements to the wiring tables, not replacements for them.
