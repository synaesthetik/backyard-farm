---
phase: 01-hardware-foundation-and-sensor-pipeline
plan: "03"
subsystem: infra
tags: [edge, sqlite, mqtt, paho-mqtt, ds18b20, ads1115, raspberry-pi, systemd, python, sensor-daemon, store-and-forward]

requires:
  - phase: 01-hardware-foundation-and-sensor-pipeline
    plan: "01"
    provides: "hub Docker Compose stack with Mosquitto service"
  - phase: 01-hardware-foundation-and-sensor-pipeline
    plan: "02"
    provides: "MQTT topic schema (farm/{node_id}/sensors/{type}), ACL credentials, QoS/retain contract"

provides:
  - "edge/daemon/buffer.py: SQLite store-and-forward ReadingBuffer with WAL mode and chronological flush ordering"
  - "edge/daemon/sensors.py: SensorDriver ABC with DS18B20 (1-Wire), ADS1115PHDriver (I2C pH), and MoisturePlaceholder (D-01 TBD)"
  - "edge/daemon/main.py: polling daemon with store-before-publish pattern and on_connect buffer flush (INFRA-03)"
  - "edge/daemon/tests/test_buffer.py: 6 unit tests covering all ReadingBuffer behaviors"
  - "edge/systemd/farm-daemon.service: systemd service with Restart=always and WatchdogSec=300"
  - "edge/daemon/.env.example: full configuration template for edge node deployment"

affects: [01-04, 01-05]

tech-stack:
  added:
    - paho-mqtt==2.1.0 (MQTT client with paho 2.x CallbackAPIVersion.VERSION2 API)
    - w1thermsensor==2.3.0 (DS18B20 1-Wire driver)
    - adafruit-circuitpython-ads1x15==3.0.3 (ADS1115 I2C ADC)
    - python-dotenv (environment configuration)
  patterns:
    - "Store-before-publish: buffer.store() is always called before client.publish(); mark_sent() called only on successful publish"
    - "Chronological flush: get_unsent() uses ORDER BY ts ASC so buffered readings replay in original order"
    - "Graceful hardware absence: all sensor drivers catch import/init exceptions and return None on read() failure"
    - "Pluggable driver pattern: SensorDriver ABC allows moisture driver to be swapped after D-01 research spike"
    - "paho-mqtt 2.x API: uses callback_api_version=mqtt.CallbackAPIVersion.VERSION2 and on_connect with 5 params"

key-files:
  created:
    - edge/daemon/buffer.py
    - edge/daemon/sensors.py
    - edge/daemon/main.py
    - edge/daemon/requirements.txt
    - edge/daemon/.env.example
    - edge/daemon/tests/__init__.py
    - edge/daemon/tests/conftest.py
    - edge/daemon/tests/test_buffer.py
    - edge/systemd/farm-daemon.service
  modified: []

key-decisions:
  - "Moisture driver is a placeholder returning None — D-01 research spike must select the actual sensor before driver code is written"
  - "Buffer uses WAL mode (journal_mode=WAL) for crash resilience on SD card / SSD storage"
  - "Flush stops on first publish failure to preserve chronological ordering — partial flushes are safe because unsent rows remain"
  - "poll_sensors() extracted as named function (not inlined in main loop) to satisfy plan's 'def poll_sensors' artifact requirement and improve testability"
  - "paho-mqtt 2.x CallbackAPIVersion.VERSION2 used — required for the 5-argument on_connect/on_disconnect signature"

patterns-established:
  - "Edge daemon pattern: poll loop with monotonic clock deltas (not wall-clock scheduling) for stable intervals"
  - "Sensor driver ABC: all drivers must implement read() returning float|None and sensor_type() returning string matching MQTT topic segment"

requirements-completed: [INFRA-02, INFRA-03, ZONE-01, ZONE-02, ZONE-03]

duration: 3min
completed: 2026-04-07
---

# Phase 01 Plan 03: Edge Node Sensor Daemon Summary

**SQLite store-and-forward edge daemon with DS18B20/ADS1115/moisture-placeholder sensor drivers, MQTT publish with QoS 1, and on-reconnect chronological buffer flush — all backed by 6 unit tests**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-07T19:01:30Z
- **Completed:** 2026-04-07T19:03:40Z
- **Tasks:** 2/2
- **Files modified:** 9 created

## Accomplishments

- ReadingBuffer class with WAL-mode SQLite; store-before-publish pattern guarantees no data loss during network outages (INFRA-03)
- Chronological flush ordering: get_unsent() uses ORDER BY ts ASC so replayed readings reach the hub in original timestamp order
- SensorDriver ABC with three concrete drivers; all hardware failures are caught and return None (graceful degradation without crashing the loop)
- Full 6-test suite covering store/retrieve, mark_sent, chronological order, bulk insert (1000 rows), limit, and auto-init

## Task Commits

1. **Task 1 (TDD): SQLite store-and-forward buffer with tests** - `ef5efbd` (feat)
2. **Task 2: Sensor drivers and MQTT polling daemon** - `196dbeb` (feat)

## Files Created/Modified

- `edge/daemon/buffer.py` - ReadingBuffer: WAL SQLite, store/get_unsent/mark_sent/purge_sent, ORDER BY ts ASC
- `edge/daemon/sensors.py` - SensorDriver ABC; DS18B20Driver (1-Wire), ADS1115PHDriver (I2C), MoisturePlaceholder (D-01 TBD)
- `edge/daemon/main.py` - Polling daemon: store-before-publish, on_connect flush, heartbeat with retain=true, SIGTERM/SIGINT handling
- `edge/daemon/requirements.txt` - paho-mqtt 2.1.0, w1thermsensor, adafruit-circuitpython-ads1x15, python-dotenv
- `edge/daemon/.env.example` - NODE_ID, MQTT_HOST/PORT/USER/PASS, POLL_INTERVAL_SECONDS, BUFFER_DB, FLUSH_BATCH_SIZE
- `edge/daemon/tests/conftest.py` - tmp_db pytest fixture using tmp_path
- `edge/daemon/tests/test_buffer.py` - 6 tests covering all ReadingBuffer contract behaviors
- `edge/systemd/farm-daemon.service` - Type=simple, Restart=always, RestartSec=10, WatchdogSec=300, EnvironmentFile

## Decisions Made

- Moisture driver is a placeholder returning None — D-01 research spike must select the actual sensor model before implementing the real driver. The SensorDriver ABC is designed so the class can be swapped without touching main.py.
- Buffer flush stops on first publish failure (not best-effort all). This preserves strict chronological ordering — if row 50 fails, rows 51+ must not be sent out of order.
- paho-mqtt 2.x `CallbackAPIVersion.VERSION2` is required for the new 5-argument `on_connect`/`on_disconnect` signatures. The plan specified this correctly.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `edge/daemon/sensors.py: MoisturePlaceholder` — `read()` always returns None. Stub is intentional and documented (D-01 research spike pending). The daemon correctly skips None readings and does not publish or buffer them. This stub does not prevent the plan's goal (reliable sensor pipeline for temperature and pH); moisture will be wired when the hardware decision is made in plan 01-04 or later.

## Issues Encountered

None.

## User Setup Required

Before deploying to a Pi Zero 2W edge node:
1. Copy `edge/daemon/` to `/home/pi/farm/daemon/` on the node
2. Copy `.env.example` to `.env` and fill in `MQTT_PASS` from `hub/mosquitto/generate-passwords.sh` output
3. Enable kernel modules: `dtoverlay=w1-gpio` (DS18B20) and `dtparam=i2c_arm=on` (ADS1115) in `/boot/config.txt`
4. Install Python deps: `pip3 install -r requirements.txt`
5. Install and enable systemd service: `sudo cp edge/systemd/farm-daemon.service /etc/systemd/system/ && sudo systemctl enable --now farm-daemon`

## Next Phase Readiness

- Plan 01-04 (edge local rule engine) can proceed immediately — the polling loop, sensors module, and .env pattern are established
- Plan 01-05 (hub MQTT bridge) can proceed — sensor readings will arrive at `farm/{node_id}/sensors/{type}` with the documented JSON payload format
- D-01 (moisture sensor model selection) must be resolved before the MoisturePlaceholder can be replaced with a real driver

---
*Phase: 01-hardware-foundation-and-sensor-pipeline*
*Completed: 2026-04-07*

## Self-Check: PASSED

- edge/daemon/buffer.py: FOUND
- edge/daemon/sensors.py: FOUND
- edge/daemon/main.py: FOUND
- edge/daemon/requirements.txt: FOUND
- edge/daemon/.env.example: FOUND
- edge/daemon/tests/conftest.py: FOUND
- edge/daemon/tests/test_buffer.py: FOUND
- edge/systemd/farm-daemon.service: FOUND
- .planning/phases/01-hardware-foundation-and-sensor-pipeline/01-03-SUMMARY.md: FOUND
- Commit ef5efbd: FOUND
- Commit 196dbeb: FOUND
