#!/usr/bin/env bash
# One-time local dev setup: generates MQTT credentials and writes them to config/hub.env.
# Run from the hub/ directory: bash dev-init.sh
set -euo pipefail

HUB_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HUB_DIR/../config/hub.env"
PASSWD_FILE="$HUB_DIR/mosquitto/passwd"

echo "==> Starting Mosquitto to generate credentials..."
docker compose up -d mosquitto
sleep 2

echo "==> Generating MQTT credentials..."
rm -f "$PASSWD_FILE"

BRIDGE_PASS=$(openssl rand -base64 16)
docker compose exec mosquitto mosquitto_passwd -c -b /mosquitto/config/passwd hub-bridge "$BRIDGE_PASS"
echo "hub-bridge: $BRIDGE_PASS"

for i in 01 02 03 04; do
  ZONE_PASS=$(openssl rand -base64 16)
  docker compose exec mosquitto mosquitto_passwd -b /mosquitto/config/passwd "zone-$i" "$ZONE_PASS"
  echo "zone-$i: $ZONE_PASS"
done

COOP_PASS=$(openssl rand -base64 16)
docker compose exec mosquitto mosquitto_passwd -b /mosquitto/config/passwd coop "$COOP_PASS"
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
echo "==> Done. Save the zone/coop passwords above for edge node .env files."
echo "    Run 'docker compose up' to start the full stack."
