"""Hub MQTT bridge — subscribes to all farm topics, processes readings,
writes to TimescaleDB, and notifies the dashboard WebSocket manager.

Pipeline per reading:
  1. Parse MQTT payload (Pydantic validation)
  2. Apply calibration offset (ZONE-03)
  3. Apply quality flag (INFRA-02, D-10, D-11)
  4. Check stuck detection (INFRA-07, D-12)
  5. INSERT into TimescaleDB sensor_readings hypertable
  6. Broadcast delta to WebSocket clients via HTTP notify
"""
import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone

import aiomqtt
import asyncpg
from dotenv import load_dotenv

from models import SensorPayload, HeartbeatPayload, QualityFlag, ProcessedReading
from quality import apply_quality_flag, StuckDetector
from calibration import CalibrationStore

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("bridge")

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_BRIDGE_USER", "hub-bridge")
MQTT_PASS = os.getenv("MQTT_BRIDGE_PASS", "")
DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("POSTGRES_USER", "farm")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "farm_local_dev")
DB_NAME = os.getenv("POSTGRES_DB", "farmdb")
API_NOTIFY_URL = os.getenv("API_NOTIFY_URL", "http://api:8000/internal/notify")

INSERT_READING_SQL = """
INSERT INTO sensor_readings (time, zone_id, sensor_type, value, quality, stuck, raw_value, calibration_applied, received_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
"""

INSERT_HEARTBEAT_SQL = """
INSERT INTO node_heartbeats (node_id, heartbeat_at)
VALUES ($1, $2)
"""

stuck_detector = StuckDetector()
calibration_store = CalibrationStore()


async def process_sensor_message(payload_bytes: bytes, db_pool: asyncpg.Pool) -> dict | None:
    """Process a sensor reading through the full pipeline."""
    try:
        data = json.loads(payload_bytes)
        sensor = SensorPayload(**data)
    except Exception as e:
        logger.warning("Invalid sensor payload: %s", e)
        return None

    # Step 1: Apply calibration (ZONE-03)
    calibrated_value, cal_applied = calibration_store.apply_calibration(
        sensor.zone_id, sensor.sensor_type, sensor.value
    )

    # Step 2: Apply quality flag on calibrated value (D-10)
    quality = apply_quality_flag(sensor.sensor_type, calibrated_value)

    # Step 3: Check stuck detection (D-12)
    is_stuck = stuck_detector.check(sensor.zone_id, sensor.sensor_type, calibrated_value)

    received_at = datetime.now(timezone.utc)

    # Step 4: Write to TimescaleDB
    await db_pool.execute(
        INSERT_READING_SQL,
        sensor.ts,
        sensor.zone_id,
        sensor.sensor_type,
        calibrated_value,
        quality.value,
        is_stuck,
        sensor.value,
        cal_applied,
        received_at,
    )

    # Return delta for WebSocket broadcast
    return {
        "type": "sensor_update",
        "zone_id": sensor.zone_id,
        "sensor_type": sensor.sensor_type,
        "value": calibrated_value,
        "quality": quality.value,
        "stuck": is_stuck,
        "received_at": received_at.isoformat(),
    }


async def process_heartbeat_message(payload_bytes: bytes, db_pool: asyncpg.Pool) -> dict | None:
    """Process a heartbeat message."""
    try:
        data = json.loads(payload_bytes)
        hb = HeartbeatPayload(**data)
    except Exception as e:
        logger.warning("Invalid heartbeat payload: %s", e)
        return None

    await db_pool.execute(INSERT_HEARTBEAT_SQL, hb.node_id, hb.ts)

    return {
        "type": "heartbeat",
        "node_id": hb.node_id,
        "ts": hb.ts.isoformat(),
        "uptime_seconds": hb.uptime_seconds,
    }


async def notify_api(delta: dict):
    """Send delta to FastAPI internal endpoint for WebSocket broadcast."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_NOTIFY_URL, json=delta, timeout=aiohttp.ClientTimeout(total=2)):
                pass
    except Exception:
        pass  # Non-critical — dashboard may not be connected


async def bridge_loop(db_pool: asyncpg.Pool):
    """Main MQTT subscriber loop."""
    logger.info("Starting bridge loop — connecting to %s:%d", MQTT_HOST, MQTT_PORT)

    while True:
        try:
            async with aiomqtt.Client(
                MQTT_HOST,
                port=MQTT_PORT,
                username=MQTT_USER,
                password=MQTT_PASS,
            ) as client:
                await client.subscribe("farm/+/sensors/#")
                await client.subscribe("farm/+/heartbeat")
                logger.info("Subscribed to farm/+/sensors/# and farm/+/heartbeat")

                async for message in client.messages:
                    topic = str(message.topic)
                    delta = None

                    if "/sensors/" in topic:
                        delta = await process_sensor_message(message.payload, db_pool)
                    elif topic.endswith("/heartbeat"):
                        delta = await process_heartbeat_message(message.payload, db_pool)

                    if delta:
                        await notify_api(delta)

        except aiomqtt.MqttError as e:
            logger.error("MQTT error: %s — reconnecting in 5s", e)
            await asyncio.sleep(5)


async def main():
    db_pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME,
        min_size=2, max_size=10,
    )
    logger.info("Connected to TimescaleDB at %s:%d", DB_HOST, DB_PORT)

    await calibration_store.load_from_db(db_pool)

    await bridge_loop(db_pool)


if __name__ == "__main__":
    asyncio.run(main())
