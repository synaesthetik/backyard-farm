# Garden Zone Edge Node

This document covers wiring a single garden zone edge node. Build one node per garden zone.
All 4 zone nodes are identical except for the soil moisture sensor I2C address — see the
"Per-Zone Configuration" section at the end.

**Hardware:** Raspberry Pi Zero 2W + 3 sensors (soil moisture, pH, temperature)
**Purpose:** Publishes soil moisture (VWC %), soil pH, and soil temperature every 60 seconds to the hub via MQTT.

## Parts Needed

From the [Master BOM](bom.md):

| Component | BOM Section | Qty per Node |
|-----------|------------|-------------|
| Raspberry Pi Zero 2W | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| Samsung Pro Endurance microSD 32GB | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| Adafruit STEMMA Soil Sensor (ID 4026) | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| Adafruit ADS1115 ADC breakout (ID 1085) | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| DS18B20 waterproof temperature probe | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| 4.7kΩ resistor | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| DFRobot Analog pH Meter V2 (SEN0161-V2) | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| JST PH 2mm 4-pin cable | [Section 2: Garden Nodes](bom.md#section-2-garden-zone-edge-nodes-4) | 1 |
| 22AWG Dupont jumper wire assortment | [Section 5: Power](bom.md#section-5-power-enclosures-and-wiring) | shared |

Also needed from [power.md](power.md): 12V PSU + LM2596 buck converter + IP65 enclosure.

## Overview Diagram

![Garden node wiring diagram](fritzing/garden-node.png)
Source: `docs/hardware/fritzing/garden-node.fzz`

> All three sensors connect to the Pi's I2C bus (GPIO2/GPIO3) and/or 1-Wire bus (GPIO4).
> The I2C bus is shared — STEMMA soil sensor and ADS1115 both connect to the same SDA/SCL pins.
> The DS18B20 uses a completely separate 1-Wire bus on GPIO4.

## Wiring Table

| Connection | From | To | Wire Color | Notes |
|------------|------|----|-----------|-------|
| 3.3V power | Pi Physical Pin 1 (3.3V) | STEMMA VIN | Red | STEMMA can also use Pin 17 (3.3V) |
| GND | Pi Physical Pin 6 (GND) | STEMMA GND | Black | |
| I2C SDA | Pi Physical Pin 3 (GPIO2) | STEMMA SDA | Blue | Shared with ADS1115 |
| I2C SCL | Pi Physical Pin 5 (GPIO3) | STEMMA SCL | Yellow | Shared with ADS1115 |
| 3.3V power | Pi Physical Pin 17 (3.3V) | ADS1115 VDD | Red | |
| GND | Pi Physical Pin 9 (GND) | ADS1115 GND | Black | |
| I2C SDA | Pi Physical Pin 3 (GPIO2) | ADS1115 SDA | Blue | Shared bus — both sensors on same pins |
| I2C SCL | Pi Physical Pin 5 (GPIO3) | ADS1115 SCL | Yellow | Shared bus |
| ADS1115 address (GND) | ADS1115 ADDR | GND | Black | ADDR to GND → I2C address 0x48 |
| pH probe signal | DFRobot pH probe BNC output | ADS1115 A0 | — | Use the BNC cable included with pH meter V2 |
| pH probe GND | DFRobot pH probe GND | ADS1115 GND (or Pi GND) | Black | |
| 3.3V power | Pi Physical Pin 1 (3.3V) | DS18B20 VCC (red wire) | Red | DS18B20 has 3-wire cable: red/black/yellow |
| GND | Pi Physical Pin 6 (GND) | DS18B20 GND (black wire) | Black | |
| 1-Wire data | Pi Physical Pin 7 (GPIO4) | DS18B20 DQ (yellow wire) | White | |
| Pull-up resistor | DS18B20 VCC | DS18B20 DQ | — | 4.7kΩ between VCC and DQ — REQUIRED |

> **The 4.7kΩ pull-up resistor is the most commonly missed component.** Without it, the DS18B20
> will not appear in `/sys/bus/w1/devices/`. Connect one leg of the resistor to 3.3V (Pin 1)
> and the other leg to the DQ wire (yellow) between the Pi pin and the sensor.

## GPIO Pin Assignment Table

| GPIO (BCM) | Physical Pin | Function | Connected To |
|------------|-------------|----------|-------------|
| GPIO2 | Pin 3 | I2C SDA | STEMMA SDA, ADS1115 SDA (shared bus) |
| GPIO3 | Pin 5 | I2C SCL | STEMMA SCL, ADS1115 SCL (shared bus) |
| GPIO4 | Pin 7 | 1-Wire data | DS18B20 DQ |
| — | Pin 1 | 3.3V power | STEMMA VIN, DS18B20 VCC, pull-up resistor |
| — | Pin 17 | 3.3V power | ADS1115 VDD |
| — | Pin 6 | GND | STEMMA GND, DS18B20 GND |
| — | Pin 9 | GND | ADS1115 GND |

**I2C address summary for this node:**

| Device | I2C Address | Set By |
|--------|------------|--------|
| STEMMA Soil Sensor | 0x36 (zone-01 default) | Solder jumpers AD0/AD1 on STEMMA board |
| ADS1115 ADC | 0x48 (default) | ADDR pin wired to GND |

## Enabling I2C and 1-Wire on Raspberry Pi OS

Before the sensors can be read, two Linux kernel modules must be enabled:

```bash
# 1. Enable I2C
sudo raspi-config
# → Interface Options → I2C → Enable

# 2. Enable 1-Wire (add to /boot/firmware/config.txt on Bookworm, or /boot/config.txt on older)
echo "dtoverlay=w1-gpio" | sudo tee -a /boot/firmware/config.txt
sudo reboot

# 3. After reboot, verify I2C devices are visible:
sudo i2cdetect -y 1
# Expected output shows 36 at address 0x36 and 48 at address 0x48:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 30: -- -- -- -- -- -- 36 -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --

# 4. Verify DS18B20 is visible:
ls /sys/bus/w1/devices/
# Expected: 28-xxxxxxxxxxxx (one entry per DS18B20 sensor)
```

## Config File Cross-Reference

| Hardware Connection | Config Variable / Constant | File | Current Value |
|--------------------|---------------------------|------|---------------|
| STEMMA soil sensor I2C address | hardcoded `addr=0x36` | `edge/daemon/sensors.py` | 0x36 (zone-01); update per Per-Zone table below |
| ADS1115 pH ADC I2C address | `ADS1115PHDriver.i2c_address` | `edge/daemon/sensors.py` | 0x48 |
| DS18B20 1-Wire | auto-detected via w1thermsensor | `edge/daemon/sensors.py` | GPIO4 (kernel default) |
| MQTT moisture topic | topic pattern | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/sensors/moisture` |
| MQTT pH topic | topic pattern | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/sensors/ph` |
| MQTT temperature topic | topic pattern | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/sensors/temperature` |
| MQTT heartbeat topic | topic pattern | `docs/mqtt-topic-schema.md` | `farm/{zone_id}/heartbeat` |
| Hub IP (MQTT broker) | HUB_IP | `config/hub.env` | 192.168.1.100 |
| MQTT port | MQTT_PORT | `config/hub.env` | 1883 |
| Node MQTT credentials | node_id | `hub/mosquitto/passwd` | zone-01 through zone-04 |

> **Note on STEMMA driver:** `edge/daemon/sensors.py` currently contains a `MoisturePlaceholder`
> class for the soil sensor. When the actual Adafruit STEMMA Soil Sensor is connected,
> update this driver to use the `adafruit-circuitpython-seesaw` library at I2C address 0x36
> (or per-zone address from the table below). See `pip install adafruit-circuitpython-seesaw`.

## Smoke Test

Perform after wiring and OS configuration, before starting the edge daemon.

**Step 1 — Verify Pi Zero 2W boots**
```bash
ssh pi@[node-ip]
uptime
# Expected: login succeeds, no kernel errors in dmesg
```

**Step 2 — Verify I2C sensors visible**
```bash
sudo i2cdetect -y 1
```
Expected: address 0x36 (STEMMA) and 0x48 (ADS1115) both visible. If either is missing:
- 0x36 missing: check STEMMA power (VIN → 3.3V), SDA/SCL connections, JST cable orientation
- 0x48 missing: check ADS1115 power (VDD → 3.3V), SDA/SCL connections, ADDR pin wired to GND

**Step 3 — Verify DS18B20 temperature sensor**
```bash
ls /sys/bus/w1/devices/
# Expected: 28-xxxxxxxxxxxx directory

cat /sys/bus/w1/devices/28-*/w1_slave
# Expected: last line contains t=XXXXX (temperature × 1000, e.g., t=22500 = 22.5°C)
```
If directory is empty: check 4.7kΩ pull-up resistor between VCC and DQ. This is the most common cause.

**Step 4 — Verify soil moisture sensor reads (quick Python test)**
```bash
pip install adafruit-circuitpython-seesaw
python3 -c "
import board, busio
from adafruit_seesaw.seesaw import Seesaw
i2c = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c, addr=0x36)
print(f'Moisture: {ss.moisture_read()} (200=dry, 2000=wet)')
print(f'Temp: {ss.get_temp():.1f}°C')
"
# Insert probe tip into a glass of water — moisture value should be above 1000
```

**Step 5 — Start edge daemon and verify MQTT publishing**
On the hub:
```bash
docker exec mosquitto mosquitto_sub -h localhost \
  -t "farm/zone-01/#" -v \
  -u hub-bridge -P [MQTT_BRIDGE_PASS from config/hub.env]
```
On the node, start the daemon. Within 60 seconds, MQTT messages should appear:
```
farm/zone-01/sensors/moisture {"zone_id": "zone-01", "sensor_type": "moisture", ...}
farm/zone-01/sensors/ph {...}
farm/zone-01/sensors/temperature {...}
farm/zone-01/heartbeat {...}
```

**Step 6 — Verify data in TimescaleDB**
On hub:
```bash
docker exec timescaledb psql -U postgres -d farm \
  -c "SELECT zone_id, sensor_type, value, quality_flag, created_at FROM sensor_readings WHERE zone_id='zone-01' ORDER BY created_at DESC LIMIT 5;"
```
Expected: Rows with quality_flag = 'GOOD' for moisture, ph, temperature.

## Per-Zone I2C Address Configuration

Build 4 identical nodes — but set each STEMMA soil sensor to a unique I2C address:

| Zone | Zone ID | STEMMA I2C Address | STEMMA Solder Jumpers |
|------|---------|--------------------|----------------------|
| Zone 1 | zone-01 | 0x36 | AD0=open, AD1=open (default) |
| Zone 2 | zone-02 | 0x37 | AD0=bridged, AD1=open |
| Zone 3 | zone-03 | 0x38 | AD0=open, AD1=bridged |
| Zone 4 | zone-04 | 0x39 | AD0=bridged, AD1=bridged |

To bridge a solder jumper: apply a small blob of solder across the two pads labeled AD0 or AD1
on the STEMMA PCB. Use a fine-tip soldering iron. The pads are tiny — use flux if available.

The ADS1115 (pH ADC) stays at 0x48 on all nodes — each node is a separate Pi, so there
is no address conflict.

## Common Mistakes

- **Missing 4.7kΩ pull-up resistor on DS18B20** — The sensor will not appear in
  `/sys/bus/w1/devices/`. This single resistor between VCC (3.3V) and DQ (data) is
  mandatory. It is easy to overlook because it is not on the sensor board itself.

- **Adding external I2C pull-up resistors** — Do not add external 4.7kΩ or 10kΩ pull-ups
  to the SDA/SCL lines. The Pi has built-in 1.8kΩ pull-ups on GPIO2/GPIO3, and the
  STEMMA sensor adds its own 10kΩ. Additional pull-ups make the bus unstable.

- **All 4 zone nodes having the same STEMMA I2C address** — If two nodes share address 0x36,
  the hub cannot distinguish between them. Use solder jumpers to assign unique addresses
  (0x36–0x39) per the per-zone table above.

- **Connecting pH probe directly to Pi GPIO** — The DFRobot pH probe outputs an analog
  voltage (0–3.3V). The Pi has no analog input pins. The ADS1115 ADC is required in
  between. Connect the BNC cable output from the pH probe board to the ADS1115 A0 input.

- **Powering sensors from GPIO DATA pins instead of power pins** — Always use the dedicated
  3.3V power pins (Physical Pin 1 and Pin 17) and GND pins (Physical Pin 6, 9, etc.)
  for sensor power. GPIO data pins are signal-only and cannot safely source sensor power.

---

*This document covers DOC-02 (garden zone). See also: [bom.md](bom.md) · [hub.md](hub.md) · [irrigation.md](irrigation.md) · [coop-node.md](coop-node.md) · [power.md](power.md)*
