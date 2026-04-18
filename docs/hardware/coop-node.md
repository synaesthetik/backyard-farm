# Coop Edge Node

The coop edge node is the most complex hardware in the platform. It controls the chicken
coop door (via a linear actuator), monitors feed weight (load cells), monitors water level
(float switch), and reads coop temperature (DS18B20 probe). Unlike the garden zone nodes
(Pi Zero 2W), the coop node uses a Raspberry Pi 5 4GB for ONNX inference capability.

**Hardware:** Raspberry Pi 5 4GB
**Actuators:** 12V linear actuator (via L298N H-bridge), 2× limit switches
**Sensors:** 2× HX711 load cells, water level float switch, DS18B20 temperature probe
**Expansion:** 4-channel relay board (pre-wired, spare channels for future use)

## Parts Needed

From the [Master BOM](bom.md):

| Component | BOM Section | Qty |
|-----------|------------|-----|
| Raspberry Pi 5 4GB | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |
| Samsung Pro Endurance microSD 32GB | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |
| ECO-WORTHY 12V linear actuator | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |
| Roller limit switch (NO type) | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 2 |
| L298N dual H-bridge motor driver module | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |
| HX711 + 5kg load cell kit | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 2 |
| Water level float switch | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |
| DS18B20 waterproof temperature probe | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |
| 4.7kΩ resistor | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |
| 4-channel optocoupler relay board | [Section 3: Coop Node](bom.md#section-3-coop-edge-node-1) | 1 |

Also needed from [power.md](power.md): 12V 5A IP65 power supply (for actuator + relay board + 12V rail) + official Pi 5 PSU for Pi 5V power.

## Overview Diagram

![Coop node wiring diagram](fritzing/coop-node.png)
Source: `docs/hardware/fritzing/coop-node.fzz`

> The coop node uses two separate power rails:
> - **5V** from the official Pi 5 PSU → Pi 5 USB-C → Pi GPIO 5V pins → HX711 VCC, L298N logic
> - **12V** from IP65 PSU → L298N motor input → actuator motor, relay board coils
>
> Keep 5V and 12V wiring physically separated. Use orange wire for all 12V runs.

## Wiring Tables

### A — Linear Actuator (Pi 5 → L298N → 12V Actuator)

The L298N H-bridge module controls the linear actuator motor direction and speed. The Pi
sets GPIO direction pins to move the actuator in or out.

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| Direction pin A | Pi GPIO17 (Pin 11) | L298N IN1 | Green | HIGH + LOW = motor extends (door opens) |
| Direction pin B | Pi GPIO27 (Pin 13) | L298N IN2 | Green | LOW + HIGH = motor retracts (door closes) |
| Motor enable | Pi GPIO22 (Pin 15) | L298N ENA | Green | Set HIGH for full speed; PWM for speed control |
| 5V logic (L298N) | Pi Physical Pin 2 (5V) | L298N +5V (if module has 5V input) | Red | Check module — some generate 5V internally from 12V |
| GND (common) | Pi Physical Pin 6 (GND) | L298N GND | Black | MUST be common GND with 12V PSU GND |
| 12V motor power | 12V PSU positive terminal | L298N 12V input terminal | Orange | Powers the actuator motor |
| 12V GND | 12V PSU GND terminal | L298N GND terminal | Black | |
| Actuator wire A | L298N OUT1 | Linear actuator terminal A | Orange | Polarity determines extend/retract direction |
| Actuator wire B | L298N OUT2 | Linear actuator terminal B | Orange | Swap A/B wires to reverse direction |

**Motor direction logic:**

| IN1 | IN2 | Motor Action |
|-----|-----|-------------|
| HIGH | LOW | Extends actuator → door OPENS |
| LOW | HIGH | Retracts actuator → door CLOSES |
| LOW | LOW | Motor coasts (no braking) |
| HIGH | HIGH | Motor brakes (short-circuit brake) |

> **Testing direction:** On first run, verify that "door opens" command actually opens the
> door. If the door moves in the wrong direction, swap the two actuator motor wires
> (OUT1 ↔ OUT2) at the L298N terminals. Do not swap IN1/IN2 in software.

### B — Limit Switches (Door Position Confirmation)

Two roller limit switches confirm when the door has fully reached the open or closed position.
This satisfies COOP-03 (physical limit switch confirmation via GPIO) and COOP-04 (physical
limit switches at both positions).

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 3.3V to switch (open position) | Pi Physical Pin 1 (3.3V) | Limit switch A — terminal 1 | Red | |
| GPIO from switch (open position) | Limit switch A — terminal 2 | Pi GPIO5 (Pin 29) | Green | Configure as INPUT, pull-down |
| 3.3V to switch (closed position) | Pi Physical Pin 17 (3.3V) | Limit switch B — terminal 1 | Red | |
| GPIO from switch (closed position) | Limit switch B — terminal 2 | Pi GPIO6 (Pin 31) | Green | Configure as INPUT, pull-down |

**How limit switches work with pull-down configuration:**
- GPIO is configured as INPUT with internal pull-down (GPIO.PUD_DOWN)
- Default state: GPIO reads LOW (0) — switch open, door not at limit
- When door reaches position: mechanical contact closes switch → 3.3V flows through switch to GPIO → reads HIGH (1)

```python
import RPi.GPIO as GPIO

LIMIT_OPEN_PIN = 5    # BCM — door-open position switch
LIMIT_CLOSED_PIN = 6  # BCM — door-closed position switch

GPIO.setmode(GPIO.BCM)
GPIO.setup(LIMIT_OPEN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(LIMIT_CLOSED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Check door position
if GPIO.input(LIMIT_OPEN_PIN):
    print("Door is fully OPEN (limit switch triggered)")
elif GPIO.input(LIMIT_CLOSED_PIN):
    print("Door is fully CLOSED (limit switch triggered)")
else:
    print("Door is MOVING or STUCK (neither limit reached)")
```

**Physical mounting:** Mount each limit switch so the actuator body (or door frame)
depresses the roller at exactly the fully-open and fully-closed positions. The switch
should click when the door reaches the correct position. Adjust mounting if the switch
clicks too early or too late.

### C — HX711 Load Cells (GPIO Bit-Bang, Not I2C)

HX711 uses a proprietary serial protocol bit-banged via GPIO — not I2C or SPI. Two GPIO
pins per HX711: SCK (serial clock) and DOUT (data output). The Python library (hx711py) handles
the bit-bang timing.

**Feed hopper load cell:**

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| HX711 VCC | Pi Physical Pin 2 (5V) | HX711 VCC | Red | HX711 requires 5V excitation |
| HX711 GND | Pi Physical Pin 6 (GND) | HX711 GND | Black | |
| HX711 SCK (clock) | Pi GPIO23 (Pin 16) | HX711 SCK | Green | |
| HX711 DOUT (data) | Pi GPIO24 (Pin 18) | HX711 DOUT | Green | |
| Load cell red | HX711 E+ terminal | Load cell red wire | Red | Excitation positive |
| Load cell black | HX711 E− terminal | Load cell black wire | Black | Excitation negative |
| Load cell white | HX711 A− terminal | Load cell white wire | White | Signal negative |
| Load cell green | HX711 A+ terminal | Load cell green wire | Green | Signal positive |

**Nesting box load cell:**

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| HX711 VCC | Pi Physical Pin 4 (5V) | HX711 VCC | Red | Use different 5V pin to avoid current crowding |
| HX711 GND | Pi Physical Pin 9 (GND) | HX711 GND | Black | |
| HX711 SCK (clock) | Pi GPIO25 (Pin 22) | HX711 SCK | Green | Different pins from feed hopper HX711 |
| HX711 DOUT (data) | Pi GPIO8 (Pin 24) | HX711 DOUT | Green | |
| Load cell (same color mapping) | HX711 terminals | Load cell wires | (same as above) | |

> **Load cell wire colors may vary by manufacturer.** Always check the load cell datasheet.
> Common mapping: Red=E+, Black=E−, White=A−, Green=A+. If readings are negative when
> weight is added, swap A+ and A− connections.

### D — Water Level Float Switch

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 3.3V to float switch | Pi Physical Pin 17 (3.3V) | Float switch terminal 1 | Red | |
| GPIO from float switch | Float switch terminal 2 | Pi GPIO16 (Pin 36) | Green | Configure as INPUT, pull-down |

Float switch behavior:
- GPIO LOW: float is UP (water present) — normal state
- GPIO HIGH: float is DOWN (water level LOW) → trigger low-water alert

### E — DS18B20 Temperature Sensor (Coop Air Temperature)

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 3.3V power | Pi Physical Pin 1 (3.3V) | DS18B20 VCC (red wire) | Red | |
| GND | Pi Physical Pin 6 (GND) | DS18B20 GND (black wire) | Black | |
| 1-Wire data | Pi Physical Pin 7 (GPIO4) | DS18B20 DQ (yellow wire) | White | |
| Pull-up resistor | DS18B20 VCC | DS18B20 DQ | — | 4.7kΩ between VCC and DQ — REQUIRED |

### F — 4-Channel Relay Board (Pre-Wired, Expansion)

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 5V relay power | Pi Physical Pin 2 (5V) | Relay board VCC | Red | |
| GND | Pi Physical Pin 6 (GND) | Relay board GND | Black | |
| IN1 (spare) | Pi GPIO12 (Pin 32) | Relay board IN1 | Green | Available for future actuators |
| IN2 (spare) | Pi GPIO13 (Pin 33) | Relay board IN2 | Green | |
| IN3 (spare) | Pi GPIO19 (Pin 35) | Relay board IN3 | Green | |
| IN4 (spare) | Pi GPIO26 (Pin 37) | Relay board IN4 | Green | |

## GPIO Pin Assignment Table

| GPIO (BCM) | Physical Pin | Function | Connected To |
|------------|-------------|----------|-------------|
| GPIO17 | Pin 11 | L298N IN1 | Motor direction A (door open = HIGH) |
| GPIO27 | Pin 13 | L298N IN2 | Motor direction B (door close = HIGH) |
| GPIO22 | Pin 15 | L298N ENA | Motor enable (set HIGH for full speed) |
| GPIO5 | Pin 29 | Limit switch input | Door-OPEN position switch (pull-down) |
| GPIO6 | Pin 31 | Limit switch input | Door-CLOSED position switch (pull-down) |
| GPIO23 | Pin 16 | HX711 SCK | Feed hopper load cell clock |
| GPIO24 | Pin 18 | HX711 DOUT | Feed hopper load cell data |
| GPIO25 | Pin 22 | HX711 SCK | Nesting box load cell clock |
| GPIO8 | Pin 24 | HX711 DOUT | Nesting box load cell data |
| GPIO16 | Pin 36 | Float switch input | Water level (pull-down; HIGH = low water) |
| GPIO4 | Pin 7 | 1-Wire data | DS18B20 DQ (temperature) |
| GPIO12 | Pin 32 | Relay IN1 | Spare relay channel 1 |
| GPIO13 | Pin 33 | Relay IN2 | Spare relay channel 2 |
| GPIO19 | Pin 35 | Relay IN3 | Spare relay channel 3 |
| GPIO26 | Pin 37 | Relay IN4 | Spare relay channel 4 |
| — | Pin 1, 17 | 3.3V power | DS18B20 VCC, limit switches, float switch |
| — | Pin 2, 4 | 5V power | HX711 VCC (×2), L298N logic, relay board |
| — | Pin 6, 9 | GND | Common ground for all sensors |

## Config File Cross-Reference

| Hardware Connection | Config Constant | File | Current Value |
|--------------------|----------------|------|---------------|
| Actuator direction pin A (IN1) | door_open_pin IN1 | `edge/daemon/rules.py` | GPIO17 — update from stub |
| Actuator direction pin B (IN2) | door_close_pin IN2 | `edge/daemon/rules.py` | GPIO27 — update from stub |
| Actuator enable (ENA) | door_enable_pin | `edge/daemon/rules.py` | GPIO22 — update from stub |
| COOP_HARD_CLOSE action | execute_action(COOP_HARD_CLOSE) | `edge/daemon/rules.py` | Stub in Phase 1; GPIO wiring enables it |
| Limit switch — door open | limit_open_gpio | `edge/daemon/main.py` | GPIO5 — update from stub |
| Limit switch — door closed | limit_closed_gpio | `edge/daemon/main.py` | GPIO6 — update from stub |
| HX711 feed: SCK | HX711_FEED_SCK | `edge/daemon/sensors.py` | GPIO23 — update from stub |
| HX711 feed: DOUT | HX711_FEED_DOUT | `edge/daemon/sensors.py` | GPIO24 — update from stub |
| HX711 nesting: SCK | HX711_NEST_SCK | `edge/daemon/sensors.py` | GPIO25 — update from stub |
| HX711 nesting: DOUT | HX711_NEST_DOUT | `edge/daemon/sensors.py` | GPIO8 — update from stub |
| Water level float switch | float_switch_gpio | `edge/daemon/sensors.py` | GPIO16 — update from stub |
| DS18B20 temperature | auto-detected via w1thermsensor | `edge/daemon/sensors.py` | GPIO4 (kernel default) |
| Coop door command topic | command handler | `docs/mqtt-topic-schema.md` | `farm/coop/commands/coop_door` |
| Coop door ack topic | ack publisher | `docs/mqtt-topic-schema.md` | `farm/coop/ack/{command_id}` |
| Feed weight topic | sensor publisher | `docs/mqtt-topic-schema.md` | `farm/coop/sensors/feed_weight` |
| Water level topic | sensor publisher | `docs/mqtt-topic-schema.md` | `farm/coop/sensors/water_level` |
| Sunrise/sunset lat/long | HUB_LATITUDE, HUB_LONGITUDE | `hub/bridge/coop_scheduler.py` | 37.7749, -122.4194 (update to your location) |

## Smoke Test

Perform each step in order, without connecting the next component until the current step passes.

**Step 1 — Verify Pi 5 boots**
```bash
ssh pi@[coop-node-ip]
uptime
# Expected: login succeeds, no kernel errors
```

**Step 2 — Verify L298N actuator control (no actuator connected yet)**
```python
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)  # IN1
GPIO.setup(27, GPIO.OUT)  # IN2
GPIO.setup(22, GPIO.OUT)  # ENA

GPIO.output(22, GPIO.HIGH)  # Enable
GPIO.output(17, GPIO.HIGH)  # IN1 HIGH
GPIO.output(27, GPIO.LOW)   # IN2 LOW
print("Motor command: EXTEND — measure continuity between OUT1 and OUT2")
time.sleep(2)
GPIO.output(17, GPIO.LOW)
GPIO.output(27, GPIO.HIGH)
print("Motor command: RETRACT — polarity reversed")
time.sleep(2)
GPIO.cleanup()
```
Use a multimeter on OUT1/OUT2 to verify polarity reverses. No actuator needed yet.

**Step 3 — Connect actuator and test movement (no limit switches yet)**
1. Connect actuator motor wires to L298N OUT1 and OUT2
2. Run the extend command (Step 2 motor commands)
3. Actuator should extend (rod slides out)
4. Run retract command: actuator should retract
5. Let actuator reach full extension: it will stop when internal end-stop triggers
6. Verify motor stops naturally — do not command motor beyond end-stop for more than 2 seconds

**Step 4 — Test limit switches**
```bash
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)   # door-open switch
GPIO.setup(6, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)   # door-closed switch
print('Manually press door-open limit switch...')
import time; time.sleep(3)
print(f'Open switch GPIO5 reads: {GPIO.input(5)} (expected 1 when pressed)')
print('Now press door-closed limit switch...')
time.sleep(3)
print(f'Closed switch GPIO6 reads: {GPIO.input(6)} (expected 1 when pressed)')
GPIO.cleanup()
"
```
Manually press each limit switch by hand. GPIO should read 1 when switch is depressed.
If always 0: check switch terminal wiring and pull-down configuration.
If always 1: switch is wired to GND instead of 3.3V — swap connections.

**Step 5 — Test HX711 load cells**
```bash
pip install hx711py
python3 -c "
from hx711 import HX711
import time

# Feed hopper load cell
hx_feed = HX711(dout_pin=24, pd_sck_pin=23)
hx_feed.reset()
hx_feed.tare()
print('Feed cell tared. Place a known weight (e.g., 500g)...')
time.sleep(5)
reading = hx_feed.get_weight_mean(10)
print(f'Feed load cell reading: {reading:.1f} raw units')
print('Expected: ~500g (requires calibration factor from scale)')
"
```
Raw units will not equal grams until a calibration factor is applied (see edge daemon
calibration workflow). This test verifies the HX711 is communicating and responding to weight.

**Step 6 — Test float switch**
```bash
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
print('Float switch GPIO16:', GPIO.input(16))
print('0 = float up (water present), 1 = float down (low water)')
GPIO.cleanup()
"
```
Manually press the float switch body downward (simulating low water). GPIO should change.

**Step 7 — Test DS18B20 temperature sensor**
```bash
ls /sys/bus/w1/devices/
# Expected: 28-xxxxxxxxxxxx directory
cat /sys/bus/w1/devices/28-*/w1_slave
# Expected: t=XXXXX (temperature in millidegrees C)
```

**Step 8 — Verify MQTT topics on hub**
On hub:
```bash
docker exec mosquitto mosquitto_sub -h localhost \
  -t "farm/coop/#" -v \
  -u hub-bridge -P [MQTT_BRIDGE_PASS from config/hub.env]
```
Start edge daemon on coop node. Within 60 seconds, expect:
```
farm/coop/sensors/feed_weight {...}
farm/coop/sensors/water_level {...}
farm/coop/heartbeat {...}
```

## Common Mistakes

- **Forgetting to make GND common between Pi and 12V PSU** — The L298N and Pi must share a
  common GND reference. Connect Pi GND (any GND pin) to the 12V PSU GND terminal via a black
  wire. Without this, motor control signals will be floating and the motor will behave erratically.

- **Running the actuator past its end-stop for more than 2 seconds** — The ECO-WORTHY actuator
  has internal limit switches that stop the motor at stroke limits. The motor will stall briefly
  at the end-stop. This is safe for 1–2 seconds. Do not continuously command the motor against
  the end-stop — it will overheat. The software limit switch GPIO (GPIO5/GPIO6) should stop the
  motor command when the door reaches position.

- **Incorrect load cell wire color mapping** — Load cell wire colors (E+/E−/A+/A−) vary by
  manufacturer. Always verify with the load cell's datasheet or product description. If readings
  go negative when weight is added, swap the A+ and A− connections at the HX711 terminals.

- **Not taring the HX711 after mounting** — The load cell tare weight includes the mounting
  hardware and any platform. Always run `hx711.tare()` with the empty hopper/platform before
  taking weight readings. The edge daemon handles this on startup.

- **HX711 reading garbage or stuck at max** — Usually caused by incorrect SCK/DOUT pin
  assignment in software or a loose wire. Use the test script in Step 5 and trace each wire
  back to its HX711 terminal. SCK and DOUT are the most commonly swapped wires.

- **Mounting limit switches where they can't reach end-of-travel position** — Test limit switch
  triggering before final installation. The switch roller must contact the door or actuator body
  firmly at the correct position. If it doesn't click, the software will raise a STUCK DOOR alert.
