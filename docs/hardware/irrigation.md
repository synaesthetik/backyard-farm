# Irrigation — Solenoid Valve and Relay Wiring

Each garden zone has one solenoid valve that controls water flow to that zone. The valve
is controlled by a relay board connected to the Raspberry Pi Zero 2W GPIO. When the Pi
triggers the relay, 12V power flows to the solenoid and the valve opens.

**Critical safety requirement:** All solenoid valves MUST be normally-closed (NC). An NC
valve blocks water flow when unpowered. If the system loses power or the Pi reboots, the
valve stays closed — preventing flooding. (This is requirement IRRIG-03 in the software
requirements document.)

## Parts Needed

From the [Master BOM](bom.md):

| Component | BOM Section | Qty |
|-----------|------------|-----|
| U.S. Solid 3/4" NC solenoid valve 12V DC | [Section 4: Irrigation](bom.md#section-4-irrigation) | 4 (one per zone) |
| 4-channel optocoupler relay board | [Section 4: Irrigation](bom.md#section-4-irrigation) | 1 |
| 3/4" garden hose Y-splitter | [Section 4: Irrigation](bom.md#section-4-irrigation) | 1 |
| 3/4" hose-to-NPT adapter | [Section 4: Irrigation](bom.md#section-4-irrigation) | 4 |

Also needed from [power.md](power.md): 12V 5A IP65 power supply for solenoid power.
The relay board GPIO control comes from the garden zone node Pi Zero 2W.

## Overview Diagram

![Irrigation relay wiring diagram](fritzing/irrigation-relay.png)
Source: `docs/hardware/fritzing/irrigation-relay.fzz`

> Each garden zone node controls one solenoid valve via one relay channel.
> The relay board sits between the Pi's 3.3V GPIO signal and the 12V solenoid valve.
> The Pi's GPIO never touches 12V directly — the optocoupler provides complete electrical isolation.

## Wiring Table

### Relay Board Control (GPIO → Relay)

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 5V relay power | Pi Physical Pin 2 (5V) | Relay board VCC | Red | Relay board needs 5V for coils — not 3.3V |
| GND | Pi Physical Pin 6 (GND) | Relay board GND | Black | |
| Zone-01 relay control | Pi GPIO17 (Pin 11) | Relay board IN1 | Green | Active-LOW by default on most boards |
| Zone-02 relay control | Pi GPIO27 (Pin 13) | Relay board IN2 | Green | |
| Zone-03 relay control | Pi GPIO22 (Pin 15) | Relay board IN3 | Green | |
| Zone-04 relay control | Pi GPIO10 (Pin 19) | Relay board IN4 | Green | (or any available GPIO) |

> **Note:** Each garden zone node is a separate Pi Zero 2W. Each node controls its own valve via
> one relay channel. Only IN1 is used per node (one relay = one valve). The other 3 relay
> channels are spare capacity for future expansion.

### Solenoid Valve Wiring (Relay → Valve)

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 12V supply | 12V PSU positive terminal | Relay COM terminal | Orange | 12V goes to relay COM (common) |
| 12V switched | Relay NC terminal | Solenoid valve (+) wire | Orange/Purple | When relay OPENS (de-energized), NC = closed valve; when relay CLOSES (energized), 12V passes through |
| 12V return | Solenoid valve (−) wire | 12V PSU GND terminal | Black | Completes solenoid circuit |

> **NC terminal vs NO terminal:** Use the NC (normally-closed) terminal on the relay board
> for valve control — NOT the NO (normally-open) terminal. This way: relay off = 12V off =
> valve closed (NC valve behavior). This is a double safety: the relay NC terminal AND the
> valve NC construction both ensure the valve is closed when de-powered.

## GPIO Pin Assignment Table

| GPIO (BCM) | Physical Pin | Function | Connected To | Zone |
|------------|-------------|----------|-------------|------|
| GPIO17 | Pin 11 | Relay control (zone valve) | Relay board IN1 | zone-01 |
| GPIO27 | Pin 13 | Relay control (spare) | Relay board IN2 | spare |
| GPIO22 | Pin 15 | Relay control (spare) | Relay board IN3 | spare |
| GPIO10 | Pin 19 | Relay control (spare) | Relay board IN4 | spare |
| — | Pin 2 | 5V power | Relay board VCC | — |
| — | Pin 6 | GND | Relay board GND | — |

## Active-HIGH vs Active-LOW: Critical Relay Test

Most optocoupler relay boards are **active-LOW** — the relay CLOSES (contact connects) when
the GPIO pin is set LOW (0V), not HIGH (3.3V). This is counter-intuitive and critical to
get right.

**Why it matters:** On Pi boot, GPIO pins can briefly float LOW. If the relay is active-LOW
and the solenoid valve is connected, the valve will briefly open on every boot.

**Test BEFORE connecting any valve:**

```python
# Run this test on the Pi Zero 2W with relay board connected but NO valve wired to relay
import RPi.GPIO as GPIO
import time

RELAY_PIN = 17  # BCM — matches IN1 wiring above

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

print("Setting HIGH — listen for relay click...")
GPIO.output(RELAY_PIN, GPIO.HIGH)
time.sleep(2)
# HIGH = relay CLICKS (closes) → this is active-HIGH behavior
# HIGH = relay SILENT → this is active-LOW behavior

print("Setting LOW — listen for relay click...")
GPIO.output(RELAY_PIN, GPIO.LOW)
time.sleep(2)
# LOW = relay CLICKS (closes) → this is active-LOW behavior

GPIO.cleanup()
```

**Record your result here:**
- My relay board is: ☐ active-HIGH (GPIO HIGH closes relay)  ☐ active-LOW (GPIO LOW closes relay)

Update `edge/daemon/rules.py` in the `execute_action` function to use the correct GPIO
logic level when opening and closing the irrigation valve.

## Config File Cross-Reference

| Hardware Connection | Config Variable / Constant | File | Current Value |
|--------------------|---------------------------|------|---------------|
| Irrigation relay GPIO pin | IRRIGATION_RELAY_GPIO | `edge/daemon/rules.py` | GPIO17 (BCM) — stub in Phase 1, wire in Phase 2 |
| Relay active level | RELAY_ACTIVE_LEVEL | `edge/daemon/rules.py` | Determined by active-HIGH/LOW test above |
| Irrigation open command | IRRIGATION_SHUTOFF action | `edge/daemon/rules.py` | execute_action(IRRIGATION_SHUTOFF) |
| MQTT irrigation command topic | topic | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/commands/irrigate` |
| MQTT ack topic | topic | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/ack/{command_id}` |
| Single-zone-at-a-time invariant | enforced in hub bridge | `hub/bridge/main.py` | Hub rejects concurrent open commands (IRRIG-02) |

## Smoke Test

**Step 1 — Relay board power test (no valve connected)**
1. Connect relay board VCC to Pi 5V (Pin 2), GND to Pi GND (Pin 6)
2. Relay board power LED should illuminate
3. If no power LED: check VCC/GND connections

**Step 2 — Active-HIGH/LOW test (REQUIRED before connecting valve)**
1. Connect relay board to Pi GPIO WITHOUT valve or actuator connected to relay
2. Run the relay test script above
3. Listen for relay click sound when writing HIGH and LOW
4. Record whether HIGH or LOW closes the relay
5. Do not proceed until you know which logic level closes the relay

**Step 3 — Dry valve test (valve connected to relay, no water pressure)**
1. Wire valve to relay COM and NC terminals using Orange/Purple wires
2. Wire valve GND to 12V PSU GND
3. Set 12V PSU output to relay COM terminal
4. Trigger the relay (using the correct logic level from Step 2)
5. Listen for valve solenoid CLICK — confirms electrical circuit is complete
6. If no click: check 12V supply, check COM/NC terminal connections

**Step 4 — Water flow test (valve connected, water supply on)**
1. Connect water supply hose through Y-splitter → hose-to-NPT adapter → solenoid valve inlet
2. Route solenoid valve outlet to where zone irrigation should go
3. With relay OFF (valve closed): no water should flow through the valve. If water flows, you have a NO (normally-open) valve, not NC — replace it.
4. Trigger relay (valve open): water should flow
5. Deactivate relay (valve close): water should stop within 1–2 seconds

**Step 5 — MQTT command test (end-to-end)**
From the hub dashboard, send a manual irrigation command for zone-01. Confirm:
- Dashboard shows zone-01 irrigation status as "open"
- Water flows through the zone-01 valve
- After 5 seconds (or manual close), valve closes and dashboard updates

## Common Mistakes

- **Using a normally-open (NO) solenoid valve** — NO valves pass water when unpowered.
  A power outage or Pi reboot will flood the garden. Always verify the valve is NC:
  with no power applied, push water through manually — the normally-closed valve must block flow.

- **Wiring to the NO relay terminal instead of NC** — The relay board has three terminals:
  COM (common), NO (normally-open), and NC (normally-closed). Connecting the 12V to NO
  means power flows when relay is de-energized. Use the NC terminal so the valve gets power
  only when the relay is actively triggered.

- **Not running the active-HIGH/LOW test before connecting the valve** — Relay boards vary.
  Some are active-HIGH, most are active-LOW. Connecting the valve before knowing the relay's
  logic level risks a brief valve opening on every Pi boot.

- **No flyback diode protection on solenoid** — The recommended optocoupler relay boards
  include built-in flyback diodes to suppress solenoid back-EMF spikes. Do not substitute
  bare relay modules without this protection — solenoid back-EMF can damage the relay board
  or cause Pi GPIO voltage spikes.

- **Connecting solenoid valve directly to Pi GPIO** — The solenoid requires 12V and up to
  500mA. Pi GPIO pins output 3.3V at 16mA maximum. Always use the relay board in between.

---

*This document covers DOC-02 (irrigation). See also: [bom.md](bom.md) · [garden-node.md](garden-node.md) · [hub.md](hub.md) · [coop-node.md](coop-node.md) · [power.md](power.md)*
