# Troubleshooting Guide

Find your symptom below. Each entry describes what you see in the dashboard, the most likely causes, step-by-step diagnostic checks, and how to resolve it.

---

## 1. Sensor shows STALE data (reading is >5 minutes old)

**Symptom:** A zone card shows an orange or red freshness timestamp, e.g., "Last update: 12 min ago". The STALE badge is displayed.

**Possible Causes:**
- Edge node is offline or has lost Wi-Fi connectivity
- Edge node sensor daemon has crashed
- MQTT broker (Mosquitto) is not running on the hub

**Diagnostic Steps:**
1. Open the **System Health panel** (bottom of Home screen). Check if the node shows as "offline" — if yes, see [Failure Mode 5](#5-node-shows-offline-in-system-health-panel).
2. SSH to the edge node and run: `systemctl status farm-sensor` — is the daemon running?
3. On the hub, run: `docker compose ps` — is Mosquitto running?
4. On the edge node, check: `journalctl -u farm-sensor -n 50` for connection errors.

**Resolution:** Restart the sensor daemon (`systemctl restart farm-sensor`) or the Mosquitto container (`docker compose restart mosquitto`). If Wi-Fi is the issue, check signal strength or move the node closer to the router.

---

## 2. Sensor shows SUSPECT or BAD quality flag

**Symptom:** A zone card shows a yellow (SUSPECT) or red (BAD) badge next to a sensor reading. The reading may still be displayed but is not trusted.

**Possible Causes:**
- Sensor is reading outside the expected physical range
- Soil moisture sensor is not in contact with soil (probes in air)
- pH sensor needs calibration
- Temperature sensor has a wiring fault

**Diagnostic Steps:**
1. Check the reading value — is it physically plausible? (VWC >95% or <0% suggests a hardware fault)
2. Inspect the sensor physically: are the probes inserted fully in soil? Is the pH probe in liquid?
3. Check calibration: for pH, review the last calibration date in **Settings → Calibration**.
4. If the reading is implausible for any soil (e.g., VWC = 0.0% always), proceed to [Failure Mode 3](#3-sensor-returns-staticstuck-reading-same-value-for-30-readings).

**Resolution:** Re-insert sensor probes if they're loose. Recalibrate the pH sensor if overdue. Replace the sensor if the physical value is persistently implausible.

**See also:** [Garden Node Wiring and Smoke Test](../hardware/garden-node.md)

---

## 3. Sensor returns static/stuck reading (same value for 30+ readings)

**Symptom:** The STUCK badge appears on a sensor reading. The value has not changed over several minutes of readings.

**Possible Causes:**
- Sensor hardware fault (broken probe, corroded contacts)
- Sensor wiring loose or disconnected
- Sensor daemon is reading from a disconnected I2C/ADC channel (always returns 0.0)

**Diagnostic Steps:**
1. SSH to the edge node. Run: `sudo i2cdetect -y 1` — does the expected sensor address appear? (STEMMA soil sensor at 0x36, ADS1115 ADC at 0x48)
2. Verify the sensor responds to physical interaction: pour water near the moisture probe or warm the temperature sensor with your hand — does the reading change?
3. Inspect physical connections — are probe wires seated in terminal blocks?

**Resolution:** Re-seat wiring connections. If `i2cdetect` doesn't show the sensor address, check the wiring against the wiring diagram. Replace the sensor if still unresponsive.

**See also:** [Garden Node Wiring and Smoke Test](../hardware/garden-node.md)

---

## 4. Zone shows "No data received" after hardware setup

**Symptom:** A zone card exists on the dashboard but shows "No data received" with no readings.

**Possible Causes:**
- Edge node `NODE_ZONE_ID` in `config/node.env` does not match the zone ID configured in the dashboard
- MQTT credentials on the edge node are wrong or not set
- Edge node is publishing to a different MQTT topic than the hub is subscribed to

**Diagnostic Steps:**
1. Compare `NODE_ZONE_ID` in `config/node.env` on the edge node with the `zone_id` field in Zone Settings → that zone's configuration.
2. On the hub, run: `docker compose exec mosquitto mosquitto_sub -t 'farm/+/sensors' -v -u admin -P <password>` — do messages appear when the node publishes?
3. Check MQTT credentials: `NODE_MQTT_USER` and `NODE_MQTT_PASSWORD` in `config/node.env` must match the entry in `config/mosquitto_acl.conf`.

**Resolution:** Update `config/node.env` with the correct `NODE_ZONE_ID` or fix MQTT credentials, then restart the sensor daemon on the edge node.

**See also:** [MQTT Topic Schema](../mqtt-topic-schema.md)

---

## 5. Node shows offline in System Health panel

**Symptom:** The System Health panel shows a node as "offline" with a last heartbeat timestamp in the past (3 or more minutes ago).

**Possible Causes:**
- Edge node lost power
- Edge node lost Wi-Fi connectivity
- Edge node sensor daemon has crashed
- Network issue between the node and the hub

**Diagnostic Steps:**
1. Can you ping the node from the hub? `ping <node-ip>` — if no response, the node is unreachable at the network layer.
2. If unreachable: check the node's power supply (LED on Pi should be lit), check the router DHCP table for the node's MAC address.
3. If reachable: SSH to the node and check `systemctl status farm-sensor`. If crashed, check `journalctl -u farm-sensor -n 100` for the crash reason.
4. If the node rebooted due to a power glitch, the daemon should auto-restart (it is configured with `Restart=on-failure`). Check uptime: `uptime`.

**Resolution:** Restore power or Wi-Fi. Restart the daemon if it crashed. If recurring, check power supply stability — use a quality USB-C power supply rated for Pi 4 at 3A minimum.

**See also:** [Hub and Power Setup](../hardware/hub.md)

---

## 6. MQTT disconnection — bridge shows no incoming messages

**Symptom:** The bridge logs show "MQTT disconnected" or no new readings are being stored. All zones show STALE data simultaneously.

**Possible Causes:**
- Mosquitto container is not running
- Hub machine ran out of disk space (Mosquitto stops if it cannot write its persistence file)
- Mosquitto configuration error after an edit

**Diagnostic Steps:**
1. On the hub: `docker compose ps` — is the mosquitto container in a running state?
2. Check disk space: `df -h /` — if greater than 95% full, see [Failure Mode 16](#16-timescaledb-disk-full-alert).
3. Check Mosquitto logs: `docker compose logs mosquitto --tail 50`.
4. If Mosquitto restarted recently and config was edited, verify the config syntax is valid before restarting.

**Resolution:** Restart the Mosquitto container (`docker compose restart mosquitto`). If disk is full, purge old data first. If config is invalid, correct the syntax and restart.

---

## 7. Irrigation valve won't open after "Open Valve" command

**Symptom:** Clicking "Open Valve" on a zone detail screen shows the command as "sent" but the valve does not physically open. The zone irrigation status stays "closed" or returns "unknown".

**Possible Causes:**
- Edge node did not receive the MQTT command (MQTT disconnection)
- Relay board is not activating (wiring fault or relay fault)
- Solenoid valve is faulty or not receiving power
- Single-zone invariant: another zone is already open

**Diagnostic Steps:**
1. Check if another zone shows "open" status on the Home screen — the hub blocks concurrent multi-zone irrigation.
2. Check MQTT connectivity (see [Failure Mode 6](#6-mqtt-disconnection-bridge-shows-no-incoming-messages)).
3. SSH to the edge node. Manually trigger the relay using the relay test script in `edge/daemon/` — does the relay click?
4. Check relay board: use a multimeter to confirm 12V or 24V across the solenoid valve terminals when the relay is activated.
5. Apply power directly to the solenoid valve (bypassing relay) to confirm the valve opens independently.

**Resolution:** Fix the wiring or relay connection. Replace the solenoid valve if it does not open when powered directly.

**See also:** [Irrigation Relay and Solenoid Wiring](../hardware/irrigation.md)

---

## 8. Irrigation valve won't close / zone stuck irrigating

**Symptom:** A valve is open and the Close Valve command does not close it. The zone remains in "open" status. Water continues to flow.

**Possible Causes:**
- MQTT command not reaching the edge node (disconnection)
- Relay fault — relay contacts stuck in closed position (welded by overcurrent)
- Solenoid valve stuck open (debris, worn plunger)

**Diagnostic Steps:**
1. Try the Close Valve button again. If the command acknowledges but the relay does not click, the relay may be stuck.
2. SSH to edge node and run the relay test script to send a close command — does the relay click?
3. If the relay clicks but the valve stays open, the valve itself is stuck. Turn off the water supply at the main valve while you investigate.
4. If the relay does not click: test the relay board with a different relay channel.

**Resolution:** Replace the stuck relay. Normally-closed solenoid valves will close when power is removed — turning off relay board power acts as an emergency stop. Replace the solenoid valve if it is stuck open mechanically.

**See also:** [Irrigation Relay and Solenoid Wiring](../hardware/irrigation.md)

---

## 9. Coop door stuck (P0 alert fires, door didn't reach limit switch)

**Symptom:** A P0 "Coop door stuck" alert appears in the alert bar. The door state shows "stuck". The door started moving but did not complete its travel within 60 seconds.

**Possible Causes:**
- Physical obstruction in the door track
- Linear actuator limit switch wiring loose or disconnected
- Linear actuator motor failed or is underpowered
- Limit switch misaligned (not triggering at end of travel)

**Diagnostic Steps:**
1. Physically inspect the door — is there debris, a stuck bird, or ice in the track?
2. Manually move the door to the fully open or fully closed position. Do you hear the limit switch click at end of travel?
3. SSH to the coop node and run the limit switch test script from the coop node smoke test procedure — does each switch report correctly at end of travel?
4. Check limit switch wiring continuity with a multimeter.

**Resolution:** Clear any obstruction. Re-align or re-wire limit switches. If the actuator motor is running slowly or failing to reach end-of-travel, check its 12V power supply voltage and replace the actuator if needed.

**See also:** [Coop Node Wiring and Smoke Test](../hardware/coop-node.md)

---

## 10. Coop door doesn't open or close at scheduled time

**Symptom:** The door did not open at sunrise or close at sunset as configured. No stuck alert fired — the door simply did not move.

**Possible Causes:**
- Latitude and longitude not configured or entered incorrectly
- Hub system clock is wrong (affects sunrise/sunset calculation)
- Coop scheduler service on the bridge has not started or has crashed
- A hard time limit is blocking the scheduled time (e.g., `hard_open_limit` is set later than the calculated open time)

**Diagnostic Steps:**
1. Open **Coop Settings** — is a latitude and longitude set? Check that they are in decimal degrees format (e.g., 37.7749, -122.4194) not degrees/minutes/seconds.
2. On the hub, check system time: `date` — is it correct and is the timezone set correctly?
3. Check bridge logs: `docker compose logs bridge --tail 100 | grep -i coop` — are schedule times being calculated and logged?
4. Check whether the calculated open time is earlier than `hard_open_limit` in the coop configuration.

**Resolution:** Correct the latitude/longitude. Fix the hub timezone (`timedatectl set-timezone <zone>`). Adjust `hard_open_limit` if it is blocking the schedule.

---

## 11. Recommendation queue is empty when a sensor is out of range

**Symptom:** A zone card shows a low moisture reading (below the configured threshold) but no recommendation appears in the recommendation queue.

**Possible Causes:**
- A recommendation for this zone is already pending (deduplication suppresses duplicates)
- The zone is in a cool-down window after a recent irrigation event
- ML engine is in cold-start and not yet generating recommendations (if ML mode is enabled)
- The reading is flagged SUSPECT or BAD (ML and rule engine only use GOOD-flagged data)

**Diagnostic Steps:**
1. Check the Recommendations screen — is there already a pending recommendation for this zone?
2. Check the zone detail for recent irrigation — was a valve opened in the last 2 hours?
3. Open **Settings → AI** — is the ML engine in cold-start mode (insufficient training data)?
4. Check the sensor quality flag on the zone card — if SUSPECT or BAD, resolve the sensor issue first.

**Resolution:** Wait for the cool-down window to expire (default 2 hours). If ML cold-start, switch to rule-based mode temporarily (toggle in AI Settings). Fix sensor quality issues if the flag is not GOOD.

---

## 12. Recommendation appears but "Approve" does nothing

**Symptom:** A recommendation card shows in the queue. Tapping "Approve" shows a spinner but the command does not execute — the recommendation stays pending and no irrigation starts.

**Possible Causes:**
- Hub bridge API is not responding (503 error from the SvelteKit dashboard API proxy)
- Edge node for the zone is offline
- MQTT broker is down

**Diagnostic Steps:**
1. Open the browser DevTools console — is there a 503 or 500 error on the approve API call?
2. On the hub: `docker compose ps` — are the bridge and mosquitto containers running?
3. Check bridge logs: `docker compose logs bridge --tail 50` for errors.
4. Check if the edge node is online in the System Health panel.

**Resolution:** Restart the bridge container (`docker compose restart bridge`). If the edge node is offline, restore it first (see [Failure Mode 5](#5-node-shows-offline-in-system-health-panel)). If MQTT is down, see [Failure Mode 6](#6-mqtt-disconnection-bridge-shows-no-incoming-messages).

---

## 13. pH calibration overdue alert won't clear after calibration

**Symptom:** The "pH calibration overdue" alert remains in the alert bar after you have recorded a new calibration in Settings → Calibration.

**Possible Causes:**
- The calibration record was saved for the wrong zone or sensor ID
- The bridge alert engine has not re-evaluated since calibration was saved
- The calibration date stored in the database is still the old date (save did not persist)

**Diagnostic Steps:**
1. Open **Settings → Calibration** — does the calibration record for this zone show today's date?
2. If the date is still old: the save may have failed — check the bridge logs for errors at the time the calibration was submitted.
3. After confirming the date is correct, wait up to 5 minutes for the alert engine to re-evaluate (it runs on a periodic loop).

**Resolution:** Re-submit the calibration record if the save failed. If the date is correct but the alert persists after 5 minutes, restart the bridge container (`docker compose restart bridge`) to force re-evaluation.

---

## 14. ntfy push notification not delivered to phone

**Symptom:** An in-app alert fired and appeared in the alert bar, but no push notification arrived on the phone via ntfy.

**Possible Causes:**
- ntfy server URL or topic is incorrect in Settings → Notifications
- ntfy service is not reachable from the hub (network issue)
- Phone is not subscribed to the correct ntfy topic
- ntfy service itself is down

**Diagnostic Steps:**
1. Open **Settings → Notifications**. Use the **Test Notification** button. Did a test push arrive on your phone?
2. If the test fails: check the bridge logs for the ntfy dispatch error: `docker compose logs bridge --tail 50 | grep ntfy`.
3. From the hub machine, test connectivity: `curl -d "Test" <ntfy-server-url>/<topic>` — does it return 200?
4. On your phone, confirm you are subscribed to the correct topic in the ntfy app.

**Resolution:** Correct the ntfy server URL and topic in Settings → Notifications. Ensure the hub can reach your ntfy server over the network. If ntfy is self-hosted, check that its service is running.

---

## 15. Dashboard shows blank / no data after fresh install

**Symptom:** After running `docker compose up -d`, navigating to the dashboard shows either a blank page, a loading spinner that never resolves, or an error page.

**Possible Causes:**
- `scripts/dev-init.sh` was not run (database schema not initialized)
- SvelteKit build has not been compiled (production mode needs `npm run build` first)
- Caddy HTTPS redirect loop (browser cached an HTTP-only redirect)
- TimescaleDB is still starting up (can take 30–60 seconds on first boot)

**Diagnostic Steps:**
1. Check container health: `docker compose ps` — are all 5 containers (mosquitto, timescaledb, bridge, dashboard, caddy) running and healthy?
2. Check `docker compose logs timescaledb --tail 20` — look for "database system is ready to accept connections".
3. Check `docker compose logs bridge --tail 20` — look for "Application startup complete".
4. Check `docker compose logs dashboard --tail 20` — any build or startup errors?
5. Clear browser cache and retry (a stale cached redirect can cause a blank page on repeat visits).

**Resolution:** Run `bash scripts/dev-init.sh` if you haven't yet. Wait 60 seconds for TimescaleDB to initialize on first boot. If dashboard is blank after all containers are healthy, check the browser console for JavaScript errors.

---

## 16. TimescaleDB disk full alert

**Symptom:** An alert appears warning that the database is running low on disk space. The **Settings → Storage** screen shows high disk usage.

**Possible Causes:**
- Raw sensor data has accumulated past the 90-day retention window without being purged
- The automatic retention job has not run (bridge restart may be needed)
- The hub's SSD or SD card is too small for the accumulated data

**Diagnostic Steps:**
1. Open **Settings → Storage** — what is the current row count and estimated size?
2. Check disk: `df -h /` — how much free space remains?
3. Check when the last purge ran: `docker compose logs bridge --tail 100 | grep -i purge`.

**Resolution:** Trigger a **Manual Purge** from Settings → Storage. If disk is critically full, run directly: `docker compose exec timescaledb psql -U farm -c "SELECT drop_chunks('sensor_readings', INTERVAL '90 days');"`. For a long-term fix, move the data volume to a larger SSD or increase the purge frequency.

---

## 17. AI domain toggle has no effect on recommendations

**Symptom:** Toggling the ML engine ON or OFF in Settings → AI does not change the source of recommendations — they still come from the same engine.

**Possible Causes:**
- The bridge AI settings endpoint returned an error (the toggle appeared to save but did not persist)
- The ML/Rules mode is persisted in a database row that was not updated

**Diagnostic Steps:**
1. After toggling, check the bridge logs: `docker compose logs bridge --tail 30 | grep -i "ai_mode\|rules_mode"`.
2. Reload the Settings → AI page — does the toggle still show the same state you set?
3. Check the bridge API directly: `curl http://localhost:8000/api/settings/ai` — what does `ai_enabled` show?

**Resolution:** Restart the bridge container (`docker compose restart bridge`). If the toggle remains unresponsive after restart, check for bridge errors in the logs and re-toggle after the container is healthy.

---

## 18. Production drop alert fires incorrectly

**Symptom:** The "Production drop" P1 alert fires but egg counts appear normal, or the alert fires immediately after adding the flock configuration.

**Possible Causes:**
- Flock configuration is incorrect (wrong breed lay rate, wrong flock size)
- Hatch date is set too recently — age factor is 0.0 for chicks under 18 weeks
- Not enough egg count entries recorded yet (3-day rolling average requires at least 3 days of data)
- Supplemental lighting setting does not match reality (marked off when lights are on lowers expected production)

**Diagnostic Steps:**
1. Open **Coop Settings** — review breed, hatch date, flock size, and supplemental lighting settings.
2. For recently hatched flocks: if the hatch date is within the last 18 weeks, expected production should be 0. If you are seeing a drop alert, check the hatch date entry for accuracy.
3. Check how many egg count entries exist — if fewer than 3 days of entries, the rolling average may produce unexpected results.

**Resolution:** Correct flock configuration. Ensure egg counts are entered daily for at least 3 consecutive days before trusting the production drop alert.

---

## 19. Hub not reachable from phone browser (HTTPS/PWA issue)

**Symptom:** Navigating to `https://<hub-ip>` on the phone shows "Connection refused" or a certificate error that won't clear, or the PWA install banner does not appear.

**Possible Causes:**
- Hub and phone are on different network segments (IoT VLAN vs. main VLAN)
- Caddy local CA not trusted on the phone
- Hub's static IP has changed (DHCP lease renewed)
- Caddy container is not running

**Diagnostic Steps:**
1. From the phone, can you reach any other LAN device at the hub's IP address? If not, you may be on a different VLAN or subnet.
2. On the hub: `docker compose ps` — is the caddy container running?
3. Check `docker compose logs caddy --tail 20` — any certificate generation errors?
4. Confirm the hub still has the same IP: `ip addr` on the hub. Update the router DHCP reservation if the IP has changed.
5. On iOS: to trust the local CA, install the Caddy root CA certificate via Settings → General → VPN & Device Management.

**Resolution:** Ensure the phone is on the same LAN (not a guest or IoT-isolated VLAN). Re-assign the static IP if it changed. For iOS PWA install, the local CA certificate must be trusted in iOS settings before the PWA install banner will appear.

---

## 20. Power loss recovery — nodes reconnect but no data is flowing

**Symptom:** After a power outage, all containers restart and all nodes come back online, but no new sensor data appears on the dashboard. Nodes show as online in the health panel but readings are STALE.

**Possible Causes:**
- Edge node MQTT session was not re-established cleanly after the outage
- TimescaleDB container started but the bridge connected before the database was fully ready
- MQTT broker restarted with a corrupted persistence file

**Diagnostic Steps:**
1. Check bridge logs: `docker compose logs bridge --tail 50` — look for "Connected to MQTT broker" and "TimescaleDB ready" messages after the restart.
2. Check if readings are appearing in raw MQTT traffic: on the hub, subscribe to `farm/#` and watch for messages from the edge nodes.
3. Check the edge node SQLite buffer: `ls -la /home/pi/farm-node/data/sensor_buffer.db` — if the file is large, data is buffered and waiting to flush.
4. Restart the bridge to force a clean reconnection: `docker compose restart bridge`.

**Resolution:** Run `docker compose restart bridge` to force the bridge to reconnect to both MQTT and TimescaleDB cleanly. Any buffered data on edge nodes will flush automatically once MQTT is re-established (QoS 1 delivery guarantees ensure no data is lost).

---

## Not finding your issue?

Check the hardware documentation for physical component smoke tests:
- [Garden Node Wiring and Tests](../hardware/garden-node.md)
- [Coop Node Wiring and Tests](../hardware/coop-node.md)
- [Hub Assembly](../hardware/hub.md)
- [Irrigation Relay and Solenoid](../hardware/irrigation.md)

For MQTT topic structure: [MQTT Topic Schema](../mqtt-topic-schema.md)
