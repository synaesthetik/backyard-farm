# Getting Started

## Prerequisites

- Hub hardware assembled and powered (see [Hub Assembly](hardware/hub.md))
- Raspberry Pi edge node(s) assembled and on the same LAN as the hub
- Python 3.10+, Docker, and Docker Compose installed on the hub
- Static IP assigned to the hub on your router

## First Boot

1. **Clone the repository** on the hub machine:
   ```bash
   git clone <your-repo-url> backyard-farm
   cd backyard-farm
   ```

2. **Configure environment variables**:
   ```bash
   cp config/hub.env.example config/hub.env
   # Edit config/hub.env:
   # MQTT_PASSWORD — strong random password for MQTT broker
   # TIMESCALE_PASSWORD — password for TimescaleDB
   # HUB_SECRET_KEY — random 32-byte hex string for JWT signing
   ```

3. **Start the stack**:
   ```bash
   docker compose up -d
   ```
   This starts: Mosquitto (MQTT), TimescaleDB, FastAPI bridge, Caddy (HTTPS reverse proxy), SvelteKit dashboard.

4. **Initialize the database**:
   ```bash
   bash scripts/dev-init.sh
   ```

5. **Open the dashboard**: Navigate to `https://<hub-ip>` in your browser. Accept the local CA certificate on first visit — subsequent visits will not show a warning.

## Interactive Tutorial

The dashboard includes a built-in tutorial. On first visit, a banner appears offering to start it. The tutorial walks through: zone setup, sensor verification, manual irrigation, coop automation, and approving your first recommendation.

To restart the tutorial at any time: **Settings → Tutorial**.

## Adding Your First Zone

See [Zone Configuration](configuration/zones.md) for all options. A basic zone requires: name, soil type, and target VWC range.

## Next Steps

- [Add zones](configuration/zones.md) for each garden bed
- [Configure coop automation](configuration/coop.md) if you have a chicken coop
- [Review alert types](configuration/alerts.md) so you know what to expect
