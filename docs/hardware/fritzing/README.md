# Fritzing Diagrams — Source Files

This directory contains Fritzing `.fzz` source files and exported PNG images for all
wiring diagrams in the backyard farm platform hardware documentation.

## Files

| File | Type | Used In | Status |
|------|------|---------|--------|
| garden-node.fzz | Fritzing source | [garden-node.md](../garden-node.md) | Pending — author must create |
| garden-node.png | PNG export | [garden-node.md](../garden-node.md) | Pending — export from .fzz |
| coop-node.fzz | Fritzing source | [coop-node.md](../coop-node.md) | Pending — author must create |
| coop-node.png | PNG export | [coop-node.md](../coop-node.md) | Pending — export from .fzz |
| irrigation-relay.fzz | Fritzing source | [irrigation.md](../irrigation.md) | Pending — author must create |
| irrigation-relay.png | PNG export | [irrigation.md](../irrigation.md) | Pending — export from .fzz |
| power-distribution.fzz | Fritzing source | [power.md](../power.md) | Pending — author must create |
| power-distribution.png | PNG export | [power.md](../power.md) | Pending — export from .fzz |

## Why Both .fzz and .png?

The `.fzz` files are the **editable source**. The `.png` files are **exported images** that
are embedded in the Markdown documentation for easy viewing on GitHub. Both must be committed:

- Without `.fzz`: Future contributors cannot update diagrams when hardware changes
- Without `.png`: The wiring diagrams will not display in the Markdown documentation

## Creating Diagrams

See [../README.md](../README.md) for the complete Fritzing workflow.

In summary:
1. Create the breadboard view in Fritzing 1.0.6
2. Save as `[name].fzz` in this directory
3. Export as PNG at 150 DPI to `[name].png` in this directory
4. Commit both files
5. Update the "Status" column in the table above

## Important: Breadboard View Only

Always use **Breadboard view** when creating diagrams for this documentation. Do not use
Schematic view or PCB view — the target reader has no electronics background and cannot
read schematic symbols.

## Diagram Contents

### garden-node.fzz
Shows: Raspberry Pi Zero 2W → STEMMA Soil Sensor (I2C 0x36) → ADS1115 ADC (I2C 0x48) →
DS18B20 temperature probe (1-Wire GPIO4) → DFRobot pH probe (via ADS1115 channel A0)

### coop-node.fzz
Shows: Raspberry Pi 5 → L298N motor driver → 12V linear actuator → limit switches
(GPIO input) → HX711 load cells (GPIO bit-bang, 2× pairs) → DS18B20 (1-Wire GPIO4) →
float switch (GPIO input) → 4-channel relay board

### irrigation-relay.fzz
Shows: Raspberry Pi Zero 2W GPIO → 4-channel optocoupler relay board → 12V solenoid valve
NC/COM wiring → 12V power rail. Includes active-HIGH vs active-LOW trigger annotation.

### power-distribution.fzz
Shows: AC mains → 12V 5A IP65 power supply → DC distribution rail → LM2596 buck converter
(12V→5V for Pi Zero) → relay board 12V input → solenoid valve 12V feed.
Includes IP65 enclosure cable gland entry points.
