---
phase: 01-hardware-foundation-and-sensor-pipeline
plan: "02"
subsystem: infra
tags: [mqtt, mosquitto, acl, authentication, topic-schema]

requires:
  - phase: 01-hardware-foundation-and-sensor-pipeline
    plan: "01"
    provides: "hub/mosquitto directory and docker-compose.yml with mosquitto service volume mounts"

provides:
  - "Mosquitto 2.x broker configuration with explicit authentication (allow_anonymous false)"
  - "Per-node MQTT ACL: zone-01..04 and coop write-only to own topic prefix, hub-bridge superuser"
  - "MQTT topic schema: farm/{node_id}/sensors/{sensor_type} and farm/{node_id}/heartbeat"
  - "JSON payload contract for sensor readings and heartbeats with all required fields"
  - "Password generation script (generate-passwords.sh) for all farm nodes"
  - "Empty passwd placeholder for Docker Compose volume mount"

affects: [01-03, 01-05]

tech-stack:
  added: []
  patterns:
    - "MQTT topic convention: farm/{node_id}/{category}/{type} — hierarchical, node-scoped"
    - "ACL per-node isolation: each node username restricted to write only its own topic prefix"
    - "Mosquitto 2.x requires explicit listener + allow_anonymous false (no implicit defaults)"

key-files:
  created:
    - hub/mosquitto/mosquitto.conf
    - hub/mosquitto/acl
    - hub/mosquitto/generate-passwords.sh
    - hub/mosquitto/passwd
    - docs/mqtt-topic-schema.md
  modified: []

key-decisions:
  - "QoS 1 for all sensor publishes (at least once delivery) per D-09"
  - "Heartbeats retain=true, sensor readings retain=false — hub needs last-known-alive but not stale sensor values"
  - "Username = node_id pattern for ACL — eliminates separate credential-to-node mapping; topic prefix enforces isolation"
  - "Phase 2 command topics (farm/{node_id}/commands/# and ack/#) documented as reserved but not implemented"

patterns-established:
  - "MQTT ACL isolation: username matches node_id; ACL restricts writes to farm/{username}/# only"
  - "Password generation: openssl rand -base64 16 per node, mosquitto_passwd hashes and stores"

requirements-completed: [INFRA-08]

duration: 2min
completed: 2026-04-07
---

# Phase 01 Plan 02: MQTT Topic Schema and Mosquitto Authentication Summary

**Mosquitto 2.x broker configured with per-node ACL isolation and documented MQTT topic schema serving as the communication contract for edge daemon (01-03) and hub bridge (01-05)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-07T18:58:16Z
- **Completed:** 2026-04-07T19:00:00Z
- **Tasks:** 1/1
- **Files modified:** 5 created

## Accomplishments

- Mosquitto 2.x configuration with `allow_anonymous false`, password file, ACL file, persistence, and connection limits (max 50 connections)
- Per-node ACL: hub-bridge has `readwrite farm/#`; each zone node and coop restricted to `write farm/{node_id}/sensors/#` and `write farm/{node_id}/heartbeat` only
- MQTT topic schema documented with full hierarchy, JSON payload format (zone_id, sensor_type, value, ts, node_id), QoS 1 spec, retain flags, and Phase 2 reserved topics
- Password generation script creates cryptographically random credentials (openssl rand -base64 16) for all 6 nodes via mosquitto_passwd

## Task Commits

1. **Task 1: Create MQTT topic schema documentation and Mosquitto configuration** - `08c70f6` (feat)

## Files Created/Modified

- `hub/mosquitto/mosquitto.conf` - Explicit auth config: allow_anonymous false, password_file, acl_file, listener 1883, persistence, logging, max_connections 50
- `hub/mosquitto/acl` - ACL: hub-bridge superuser readwrite farm/#; zone-01..04 and coop write-only to own sensors/# and heartbeat
- `hub/mosquitto/generate-passwords.sh` - Generates random passwords for hub-bridge, zone-01..04, coop via mosquitto_passwd; executable
- `hub/mosquitto/passwd` - Empty placeholder file (populated by generate-passwords.sh before stack start)
- `docs/mqtt-topic-schema.md` - Complete MQTT contract: topic hierarchy, JSON payload fields, QoS/retain spec, node credential table, Phase 2 reserved topics

## Decisions Made

- QoS 1 (at least once delivery) for all sensor publishes per D-09 — duplicate handling is acceptable, silent drops are not
- Heartbeats use `retain=true` so hub gets last-known-alive state on reconnect; sensor readings use `retain=false` to prevent stale data misleading the dashboard
- Username = node_id pattern makes the ACL self-enforcing: the topic prefix in ACL entries matches the username, so no separate credential-to-node mapping is needed
- Phase 2 actuator command topics (`farm/{node_id}/commands/#`, `farm/{node_id}/ack/#`) documented as reserved in schema but not implemented

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Before running `docker compose up` on the hub:
1. Run `bash mosquitto/generate-passwords.sh` from the `hub/` directory to generate and store credentials
2. Copy the printed credentials into edge node `.env` files (one per node)

## Next Phase Readiness

- Plan 01-03 (edge daemon) can proceed — topic schema and ACL contract are documented; edge daemon knows which topics to publish to and what credentials to use
- Plan 01-05 (hub bridge) can proceed — hub-bridge credentials and subscribed topic prefix (`farm/#`) are defined
- Mosquitto will start correctly when Docker Compose runs — passwd placeholder prevents volume mount failure before credentials are generated

---
*Phase: 01-hardware-foundation-and-sensor-pipeline*
*Completed: 2026-04-07*

## Self-Check: PASSED

- hub/mosquitto/mosquitto.conf: FOUND
- hub/mosquitto/acl: FOUND
- hub/mosquitto/generate-passwords.sh: FOUND
- hub/mosquitto/passwd: FOUND
- docs/mqtt-topic-schema.md: FOUND
- Commit 08c70f6: FOUND
