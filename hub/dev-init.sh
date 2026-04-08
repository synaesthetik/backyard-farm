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
rm -rf "$PASSWD_FILE" && touch "$PASSWD_FILE"

BRIDGE_PASS=$(openssl rand -base64 16)
docker run --rm -v "$PASSWD_FILE:/mosquitto/config/passwd" \
  eclipse-mosquitto:2.1.2-alpine \
  mosquitto_passwd -c -b /mosquitto/config/passwd hub-bridge "$BRIDGE_PASS"
echo "hub-bridge: $BRIDGE_PASS"

for i in 01 02 03 04; do
  ZONE_PASS=$(openssl rand -base64 16)
  docker run --rm -v "$PASSWD_FILE:/mosquitto/config/passwd" \
    eclipse-mosquitto:2.1.2-alpine \
    mosquitto_passwd -b /mosquitto/config/passwd "zone-$i" "$ZONE_PASS"
  echo "zone-$i: $ZONE_PASS"
done

COOP_PASS=$(openssl rand -base64 16)
docker run --rm -v "$PASSWD_FILE:/mosquitto/config/passwd" \
  eclipse-mosquitto:2.1.2-alpine \
  mosquitto_passwd -b /mosquitto/config/passwd coop "$COOP_PASS"
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
echo "==> Done."
echo "    MQTT credentials saved to config/hub.env."
echo "    Caddy root CA trusted in macOS keychain — no cert warnings at https://localhost:8443"
echo "    Save the zone/coop passwords above for edge node .env files."
echo ""
echo "    Run 'docker compose up' to start the full stack."
