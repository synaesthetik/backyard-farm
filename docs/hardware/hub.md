# Hub Assembly

The hub is the central brain of the backyard farm platform. It runs 24/7 and hosts all
platform services via Docker Compose: the MQTT broker, TimescaleDB database, Python bridge
service, FastAPI backend, SvelteKit dashboard, and Caddy HTTPS reverse proxy.

**Hardware:** Raspberry Pi 5 8GB + M.2 HAT+ + NVMe SSD
**Software:** Raspberry Pi OS Lite (64-bit) + Docker + Docker Compose

## Parts Needed

From the [Master BOM](bom.md):

| Component | BOM Section | Qty |
|-----------|------------|-----|
| Raspberry Pi 5 8GB | [Section 1: Hub](bom.md#section-1-hub) | 1 |
| Raspberry Pi M.2 HAT+ | [Section 1: Hub](bom.md#section-1-hub) | 1 |
| M.2 NVMe SSD 256GB | [Section 1: Hub](bom.md#section-1-hub) | 1 |
| Raspberry Pi 5 Official PSU 5V/5A | [Section 1: Hub](bom.md#section-1-hub) | 1 |
| Ethernet cable (Cat5e or better) | Assumed on hand | 1 |

**Why an SSD?** TimescaleDB writes sensor readings continuously. SD cards wear out in weeks
under this write pattern. The M.2 NVMe SSD handles millions of writes reliably.

## Overview Diagram

No GPIO wiring diagram — the hub connects to the network, not to sensors.

See the network architecture:

```
                 ┌─────────────────────────┐
                 │  Raspberry Pi 5 8GB     │
                 │  (Hub)                  │
                 │                         │
  Garden nodes ──┤ Ethernet (Gigabit) ──── Router ─── Internet (optional)
  Coop node    ──┤                                     (not required)
                 │  USB-C ← Official PSU   │
                 │  PCIe ← M.2 HAT+ ← SSD │
                 └─────────────────────────┘
```

## Physical Assembly

| Step | Action | Notes |
|------|--------|-------|
| 1 | Attach M.2 HAT+ to Pi 5 bottom | Slide PCIe connector into Pi 5 HAT header; secure with standoffs included in HAT+ kit |
| 2 | Insert NVMe SSD into M.2 HAT+ slot | Push SSD into M.2 slot at angle, press flat, secure with screw |
| 3 | Insert microSD card | Used for OS only during initial setup; data goes to NVMe SSD |
| 4 | Connect Ethernet cable | Pi 5 Gigabit Ethernet port → router LAN port |
| 5 | Connect to monitor (setup only) | Micro-HDMI → monitor; needed for first boot only |
| 6 | Connect USB keyboard (setup only) | For first boot configuration |
| 7 | Plug in PSU last | Connect official 5V/5A USB-C PSU; Pi boots automatically |

## Network Configuration

| Connection | Details |
|------------|---------|
| Interface | Ethernet (Gigabit) — NOT WiFi |
| IP assignment | Static IP via router DHCP reservation (MAC-based preferred over OS-side static) |
| Default hub IP | 192.168.1.100 (set this in `config/hub.env` as HUB_IP) |
| MQTT broker port | 1883 (TCP, LAN only) |
| HTTPS port | 443 (Caddy reverse proxy) |
| TimescaleDB port | 5432 (Docker internal network only) |

**Assign a static IP:** In your router admin panel, find the Pi 5's MAC address in the
DHCP client list and reserve 192.168.1.100 for it. This ensures the hub is always at the
same address.

## Config File Cross-Reference

| Hardware Connection | Config Variable | File | Value |
|--------------------|-----------------|------|-------|
| Hub IP address | HUB_IP | `config/hub.env` | 192.168.1.100 |
| MQTT broker port | MQTT_PORT | `config/hub.env` | 1883 |
| HTTPS port (Caddy) | HUB_HTTPS_PORT | `config/hub.env` | 443 |
| TimescaleDB port | TIMESCALEDB_PORT | `config/hub.env` | 5432 |
| SSD mount path | SSD_MOUNT | `config/hub.env` | ./data/timescaledb |
| MQTT bridge user | MQTT_BRIDGE_USER | `hub/bridge/main.py` | hub-bridge |
| MQTT bridge password | MQTT_BRIDGE_PASS | `config/hub.env` | Generate via `hub/mosquitto/generate-passwords.sh` — do not hardcode |

**Security note:** Never put the actual MQTT_BRIDGE_PASS value in documentation or version
control. Run `hub/mosquitto/generate-passwords.sh` to generate credentials, then add to
`config/hub.env`.

## Software Setup

### 1. Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select: **Raspberry Pi OS Lite (64-bit)** (no desktop needed)
3. Before writing: Click the settings gear to configure:
   - Set hostname: `farm-hub`
   - Enable SSH
   - Set username and password
   - Configure WiFi only if Ethernet is unavailable during setup
4. Flash to the microSD card

### 2. First Boot

1. Insert SD card, connect Ethernet, power on
2. SSH in: `ssh pi@192.168.1.100` (or use hostname `farm-hub.local`)
3. Update OS: `sudo apt update && sudo apt upgrade -y`

### 3. Move OS to NVMe SSD (Recommended)

Using Raspberry Pi's `rpi-clone` or `raspi-config`:
- `sudo raspi-config` → Advanced Options → Boot Order → NVMe/USB boot
- Use [rpi-clone](https://github.com/billw2/rpi-clone) to clone SD to NVMe:
  `sudo rpi-clone nvme0n1`
- Reboot and verify booting from NVMe: `lsblk` should show boot from `/dev/nvme0n1`

### 4. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi
# Log out and back in
docker --version
```

### 5. Clone Repository and Start Services

```bash
git clone [your-repo-url] ~/backyard-farm
cd ~/backyard-farm
cp config/hub.env.example config/hub.env
# Edit config/hub.env: set HUB_IP to your hub's static IP
nano config/hub.env
docker compose up -d
docker compose ps
```

## Smoke Test

Perform these steps after assembly and software setup, before connecting any edge nodes.

**Step 1 — Verify boot**
```bash
ssh pi@192.168.1.100
uptime
# Expected: no errors, system up for at least 1 minute
```

**Step 2 — Verify all Docker services running**
```bash
docker compose ps
```
Expected output: All services show "Up" status:
- mosquitto (MQTT broker)
- timescaledb (database)
- bridge (sensor processing)
- api (FastAPI backend)
- dashboard (SvelteKit frontend)
- caddy (HTTPS reverse proxy)

**Step 3 — Verify MQTT broker**
```bash
docker exec mosquitto mosquitto_pub -h localhost -t farm/test -m "hello" -u hub-bridge -P [MQTT_BRIDGE_PASS]
```
Expected: No error message. If you see "Connection refused", check mosquitto container logs.

**Step 4 — Verify HTTPS dashboard**
From another device on the same network:
- Open browser: `https://192.168.1.100`
- Expected: Dashboard loads (may show empty data — that's normal before nodes are connected)
- Expected: HTTPS padlock icon (Caddy serves a locally-trusted certificate)

**Step 5 — Verify TimescaleDB**
```bash
docker exec timescaledb psql -U farm -d farmdb -c "SELECT count(*) FROM sensor_readings;"
```
Expected: Returns 0 rows (no data yet). Any SQL error means DB setup failed.

**All 5 steps pass?** Hub is ready. Proceed to [garden-node.md](garden-node.md).

## Common Mistakes

- **Using WiFi instead of Ethernet** — The hub must use Ethernet for reliability. WiFi
  dropouts cause MQTT disconnections and sensor data gaps. Reserve WiFi for edge nodes only.

- **Using a phone charger instead of the official PSU** — The Pi 5 draws up to 5A under
  Docker load. Most phone chargers supply 2–3A max. The Pi will throttle and Docker
  services will crash. Use the official Raspberry Pi 5 PSU (27W/5V/5A).

- **Running TimescaleDB on SD card** — SD cards fail under continuous write patterns within
  weeks. The NVMe SSD is required for reliable long-term operation.

- **Hardcoding MQTT_BRIDGE_PASS in config/hub.env** — Do not commit the password to git.
  Add `config/hub.env` to `.gitignore` and generate credentials with `generate-passwords.sh`.

- **Forgetting to set a static IP** — If the hub IP changes (DHCP lease renewal), all edge
  nodes will lose connectivity and stop publishing data. Always reserve the hub IP in the router.
