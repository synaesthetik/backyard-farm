"""Edge node sensor daemon.

Polls sensors on configurable interval, stores every reading in SQLite buffer
before MQTT publish, flushes unsent readings on reconnect (INFRA-03).
Publishes heartbeat every 60 seconds.
"""
import os
import json
import time
import logging
import signal
import sys
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from buffer import ReadingBuffer
from rules import LocalRuleEngine, execute_action
from sensors import DS18B20Driver, ADS1115PHDriver, MoisturePlaceholder

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("farm-daemon")

# Configuration from environment
NODE_ID = os.getenv("NODE_ID", "zone-01")
MQTT_HOST = os.getenv("MQTT_HOST", "192.168.1.100")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", NODE_ID)
MQTT_PASS = os.getenv("MQTT_PASS", "")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
BUFFER_DB = os.getenv("BUFFER_DB", "readings.db")
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60"))
FLUSH_BATCH_SIZE = int(os.getenv("FLUSH_BATCH_SIZE", "50"))
NODE_TYPE = os.getenv("NODE_TYPE", "zone")  # "zone" or "coop"
EMERGENCY_MOISTURE_SHUTOFF_VWC = float(os.getenv("EMERGENCY_MOISTURE_SHUTOFF_VWC", "95"))
COOP_HARD_CLOSE_HOUR = int(os.getenv("COOP_HARD_CLOSE_HOUR", "21"))

# State
running = True
connected = False
start_time = time.monotonic()


def signal_handler(sig, frame):
    global running
    logger.info("Shutdown signal received")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def make_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_sensor_payload(zone_id: str, sensor_type: str, value: float, ts: str) -> dict:
    return {
        "zone_id": zone_id,
        "sensor_type": sensor_type,
        "value": value,
        "ts": ts,
        "node_id": NODE_ID,
    }


def build_heartbeat_payload() -> dict:
    return {
        "node_id": NODE_ID,
        "ts": make_timestamp(),
        "uptime_seconds": int(time.monotonic() - start_time),
    }


def flush_buffer(client: mqtt.Client, buffer: ReadingBuffer):
    """Flush unsent buffered readings in chronological order (INFRA-03)."""
    unsent = buffer.get_unsent(limit=FLUSH_BATCH_SIZE)
    if unsent:
        logger.info("Flushing %d buffered readings", len(unsent))
    for row_id, topic, payload_json in unsent:
        result = client.publish(topic, payload_json, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            buffer.mark_sent(row_id)
        else:
            logger.warning("Flush publish failed for row %d: rc=%d", row_id, result.rc)
            break  # Stop flushing on first failure


def on_connect(client, userdata, flags, rc, properties=None):
    global connected
    if rc == 0:
        logger.info("Connected to MQTT broker at %s:%d", MQTT_HOST, MQTT_PORT)
        connected = True
        # Flush buffered readings on reconnect
        flush_buffer(client, userdata["buffer"])
    else:
        logger.error("MQTT connection failed: rc=%d", rc)
        connected = False


def on_disconnect(client, userdata, flags, rc, properties=None):
    global connected
    connected = False
    if rc != 0:
        logger.warning("Unexpected MQTT disconnect: rc=%d", rc)


def poll_sensors(sensors, buffer, client):
    """Poll all sensors, buffer/publish readings, and return latest values for rule evaluation."""
    ts = make_timestamp()
    latest_readings = {}

    for sensor in sensors:
        value = sensor.read()
        if value is not None:
            latest_readings[sensor.sensor_type()] = value
            topic = f"farm/{NODE_ID}/sensors/{sensor.sensor_type()}"
            payload = build_sensor_payload(NODE_ID, sensor.sensor_type(), value, ts)
            payload_json = json.dumps(payload)

            # Always buffer first (INFRA-03)
            row_id = buffer.store(topic, payload, ts)

            if connected:
                result = client.publish(topic, payload_json, qos=1)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    buffer.mark_sent(row_id)

    return latest_readings


def main():
    global connected

    # Initialize sensors
    sensors = [
        DS18B20Driver(),
        ADS1115PHDriver(),
        MoisturePlaceholder(),
    ]

    buffer = ReadingBuffer(BUFFER_DB)

    # Initialize local rule engine (INFRA-04)
    rule_engine = LocalRuleEngine(
        node_type=NODE_TYPE,
        moisture_shutoff_vwc=EMERGENCY_MOISTURE_SHUTOFF_VWC,
        coop_hard_close_hour=COOP_HARD_CLOSE_HOUR,
    )

    # Initialize MQTT client (paho-mqtt 2.x API)
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=NODE_ID,
        userdata={"buffer": buffer},
    )
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=120)

    # Start network loop in background thread
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except Exception as e:
        logger.error("Initial MQTT connect failed: %s — will retry", e)
    client.loop_start()

    last_heartbeat = 0
    last_poll = 0

    try:
        while running:
            now = time.monotonic()

            # Poll sensors on interval
            if now - last_poll >= POLL_INTERVAL_SECONDS:
                last_poll = now
                latest_readings = poll_sensors(sensors, buffer, client)

                # Evaluate local rules (INFRA-04)
                rule_results = rule_engine.evaluate(latest_readings)
                for result in rule_results:
                    execute_action(result.action)

            # Heartbeat on interval
            if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                last_heartbeat = now
                if connected:
                    hb_topic = f"farm/{NODE_ID}/heartbeat"
                    hb_payload = json.dumps(build_heartbeat_payload())
                    client.publish(hb_topic, hb_payload, qos=1, retain=True)

            time.sleep(1)

    finally:
        logger.info("Shutting down daemon")
        client.loop_stop()
        client.disconnect()
        buffer.purge_sent(keep_hours=48)
        buffer.close()


if __name__ == "__main__":
    main()
