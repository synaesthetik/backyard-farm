#!/usr/bin/env bash
# Generate Mosquitto password file for all farm nodes.
# Run from hub/ directory: bash mosquitto/generate-passwords.sh
# Passwords are printed to stdout — save them for edge node configuration.

set -euo pipefail

PASSWD_FILE="mosquitto/passwd"

# Remove existing file to start fresh
rm -f "$PASSWD_FILE"

echo "Generating MQTT credentials..."
echo "================================"

# Hub bridge (superuser)
BRIDGE_PASS=$(openssl rand -base64 16)
docker compose exec mosquitto mosquitto_passwd -b /mosquitto/config/passwd hub-bridge "$BRIDGE_PASS" 2>/dev/null || \
  mosquitto_passwd -c -b "$PASSWD_FILE" hub-bridge "$BRIDGE_PASS"
echo "hub-bridge: $BRIDGE_PASS"

# Zone nodes
for i in 01 02 03 04; do
  ZONE_PASS=$(openssl rand -base64 16)
  docker compose exec mosquitto mosquitto_passwd -b /mosquitto/config/passwd "zone-$i" "$ZONE_PASS" 2>/dev/null || \
    mosquitto_passwd -b "$PASSWD_FILE" "zone-$i" "$ZONE_PASS"
  echo "zone-$i: $ZONE_PASS"
done

# Coop node
COOP_PASS=$(openssl rand -base64 16)
docker compose exec mosquitto mosquitto_passwd -b /mosquitto/config/passwd coop "$COOP_PASS" 2>/dev/null || \
  mosquitto_passwd -b "$PASSWD_FILE" coop "$COOP_PASS"
echo "coop: $COOP_PASS"

echo "================================"
echo "Password file: $PASSWD_FILE"
echo "Save these credentials for edge node .env files."
