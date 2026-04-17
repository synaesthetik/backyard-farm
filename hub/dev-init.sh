#!/usr/bin/env bash
# One-time local dev setup: generates MQTT credentials and writes them to config/hub.env.
# Run from the hub/ directory: bash dev-init.sh
set -euo pipefail

HUB_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HUB_DIR/../config/hub.env"
PASSWD_FILE="$HUB_DIR/mosquitto/passwd"

echo "==> Generating MQTT credentials (one-off container — no service needed)..."
# Use a one-off container so Mosquitto service never sees an empty passwd file.
# The service would crash-loop if started with an empty passwd file before credentials exist.
rm -rf "$PASSWD_FILE"

# Mount the config directory (not the file) so mosquitto_passwd -c can create the file fresh.
# File-level bind mounts require the source to exist; dir-level mounts do not.
MQCONF_DIR="$HUB_DIR/mosquitto"
MQ_IMAGE="eclipse-mosquitto:2.1.2-alpine"
MQ_RUN="docker run --rm --platform linux/arm64 -v $MQCONF_DIR:/mosquitto/config $MQ_IMAGE"

BRIDGE_PASS=$(openssl rand -base64 16)
$MQ_RUN mosquitto_passwd -c -b /mosquitto/config/passwd hub-bridge "$BRIDGE_PASS"
echo "hub-bridge: $BRIDGE_PASS"

for i in 01 02 03 04; do
  ZONE_PASS=$(openssl rand -base64 16)
  $MQ_RUN mosquitto_passwd -b /mosquitto/config/passwd "zone-$i" "$ZONE_PASS"
  echo "zone-$i: $ZONE_PASS"
done

COOP_PASS=$(openssl rand -base64 16)
$MQ_RUN mosquitto_passwd -b /mosquitto/config/passwd coop "$COOP_PASS"
echo "coop: $COOP_PASS"

echo ""
echo "==> Writing MQTT_BRIDGE_PASS to $ENV_FILE..."
if grep -q "^MQTT_BRIDGE_PASS=" "$ENV_FILE"; then
  sed -i.bak "s|^MQTT_BRIDGE_PASS=.*|MQTT_BRIDGE_PASS=$BRIDGE_PASS|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
elif grep -q "^# MQTT_BRIDGE_PASS" "$ENV_FILE"; then
  sed -i.bak "s|^# MQTT_BRIDGE_PASS.*|MQTT_BRIDGE_PASS=$BRIDGE_PASS|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
else
  echo "MQTT_BRIDGE_PASS=$BRIDGE_PASS" >> "$ENV_FILE"
fi

echo ""
echo "==> Trusting Caddy local CA on macOS..."
echo "    Starting Caddy to generate its root cert (requires the full stack)..."
docker compose up -d caddy
echo "    Waiting for Caddy to generate CA cert..."
for i in $(seq 1 15); do
  if docker compose exec caddy test -f /data/caddy/pki/authorities/local/root.crt 2>/dev/null; then
    break
  fi
  sleep 1
done

CERT_FILE="$HUB_DIR/caddy-local-root.crt"
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt "$CERT_FILE"

echo "    Installing root cert into macOS System keychain (sudo required)..."
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain "$CERT_FILE"
rm -f "$CERT_FILE"

echo ""
echo "==> Starting full stack..."
docker compose up --build -d

echo "==> Waiting for TimescaleDB to be healthy..."
for i in $(seq 1 30); do
  if docker compose exec timescaledb pg_isready -U farm -d farmdb -q 2>/dev/null; then
    echo "    TimescaleDB ready."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "    ERROR: TimescaleDB did not become healthy after 30s"
    exit 1
  fi
  sleep 1
done

echo ""
echo "==> Running database migrations..."
for migration in "$HUB_DIR"/migrations/*.sql; do
  if [ -f "$migration" ]; then
    echo "    Applying $(basename "$migration")..."
    cat "$migration" | docker compose exec -T timescaledb psql -U farm -d farmdb -q 2>&1 | grep -v "^$" || true
  fi
done

echo ""
echo "==> Seeding zone configuration..."
docker compose exec -T timescaledb psql -U farm -d farmdb -q <<'EOSQL'
INSERT INTO zone_config (zone_id, name, plant_type, soil_type, target_vwc_min, target_vwc_max, target_ph_min, target_ph_max)
VALUES
  ('zone-01', 'Raised Beds (Tomatoes)', 'tomato', 'loam', 25.0, 45.0, 6.0, 6.8),
  ('zone-02', 'Herb Garden', 'herbs', 'sandy_loam', 20.0, 40.0, 6.0, 7.0),
  ('zone-03', 'Berry Patch', 'blueberry', 'acidic_peat', 30.0, 50.0, 4.5, 5.5),
  ('zone-04', 'Root Vegetables', 'carrot', 'loam', 25.0, 45.0, 6.0, 6.8)
ON CONFLICT (zone_id) DO NOTHING;

INSERT INTO calibration_offsets (zone_id, sensor_type, offset_value, last_calibration_date)
VALUES
  ('zone-01', 'ph', 0.1, NOW() - INTERVAL '20 days'),
  ('zone-02', 'ph', -0.05, NOW() - INTERVAL '3 days'),
  ('zone-03', 'ph', 0.0, NULL),
  ('zone-04', 'ph', 0.2, NOW() - INTERVAL '13 days')
ON CONFLICT (zone_id, sensor_type) DO UPDATE SET
  last_calibration_date = EXCLUDED.last_calibration_date;
EOSQL

echo ""
echo "==> Generating synthetic sensor data (6 weeks, 4 zones)..."
DB_HOST=localhost python "$HUB_DIR/../scripts/generate_synthetic_data.py" \
  --weeks 6 --zones "zone-01,zone-02,zone-03,zone-04" --flock-size 12

echo ""
echo "==> Restarting bridge (picks up new data and migrations)..."
docker compose restart bridge

echo ""
echo "==> Done."
echo "    MQTT credentials saved to config/hub.env."
echo "    Caddy root CA trusted in macOS keychain — no cert warnings at https://localhost:8443"
echo "    Zones seeded: zone-01 through zone-04 with 6 weeks of sensor data."
echo "    Calibration data seeded with mixed overdue/current states."
echo "    Save the zone/coop passwords above for edge node .env files."
echo ""
echo "    Dashboard: https://localhost:8443"
