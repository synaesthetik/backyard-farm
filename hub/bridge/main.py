"""Hub MQTT bridge — subscribes to all farm topics, processes readings,
writes to TimescaleDB, and notifies the dashboard WebSocket manager.

Pipeline per reading:
  1. Parse MQTT payload (Pydantic validation)
  2. Apply calibration offset (ZONE-03)
  3. Apply quality flag (INFRA-02, D-10, D-11)
  4. Check stuck detection (INFRA-07, D-12)
  5. INSERT into TimescaleDB sensor_readings hypertable
  6. Evaluate rules / alerts / health score (Phase 2)
  7. Broadcast delta to WebSocket clients via HTTP notify
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
from rule_engine import RuleEngine
from alert_engine import AlertEngine
from health_score import compute_health_score
from irrigation_loop import IrrigationLoop
from zone_config import ZoneConfigStore, FEED_MAX_WEIGHT_GRAMS, WATER_MAX_LEVEL, FEED_LOW_THRESHOLD_PCT, WATER_LOW_THRESHOLD_PCT
from coop_scheduler import coop_scheduler_loop, mark_coop_ack_received

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

# Phase 2 engine instances
rule_engine = RuleEngine()
alert_engine = AlertEngine()
irrigation_loop = IrrigationLoop()
zone_config_store = ZoneConfigStore()

# In-memory zone sensor cache for health score computation
# Structure: { zone_id: { sensor_type: {"value": float, "quality": str} } }
_zone_sensor_cache: dict[str, dict] = {}


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

    sensor_delta = {
        "type": "sensor_update",
        "zone_id": sensor.zone_id,
        "sensor_type": sensor.sensor_type,
        "value": calibrated_value,
        "quality": quality.value,
        "stuck": is_stuck,
        "received_at": received_at.isoformat(),
    }

    # Step 5: Phase 2 engine evaluation
    await _evaluate_phase2(sensor.zone_id, sensor.sensor_type, calibrated_value, quality.value)

    return sensor_delta


async def _evaluate_phase2(zone_id: str, sensor_type: str, value: float, quality_str: str):
    """Run rule engine, alert engine, health score, and irrigation loop checks.

    Called after every sensor write. Broadcasts any resulting deltas.
    """
    zone_config = zone_config_store.get(zone_id)

    # Update zone sensor cache for health score computation
    if zone_id not in _zone_sensor_cache:
        _zone_sensor_cache[zone_id] = {}
    _zone_sensor_cache[zone_id][sensor_type] = {"value": value, "quality": quality_str}

    # --- Rule engine: generate irrigation recommendation if VWC low ---
    recommendation = rule_engine.evaluate_zone(zone_id, sensor_type, value, zone_config)
    if recommendation:
        await notify_api({
            "type": "recommendation_queue",
            "recommendations": rule_engine.get_pending_recommendations(),
        })

    # --- Alert engine: evaluate threshold crossings ---
    alert_changed = False

    if sensor_type == "moisture":
        changed, _ = alert_engine.evaluate(
            f"moisture_low:{zone_id}", value, zone_config.vwc_low_threshold, clear_above=True
        )
        if changed:
            alert_changed = True

    elif sensor_type == "ph":
        changed_low, _ = alert_engine.evaluate(
            f"ph_low:{zone_id}", value, zone_config.ph_low_threshold, clear_above=True
        )
        changed_high, _ = alert_engine.evaluate(
            f"ph_high:{zone_id}", value, zone_config.ph_high_threshold, clear_above=False
        )
        if changed_low or changed_high:
            alert_changed = True

    elif sensor_type == "temperature":
        changed_low, _ = alert_engine.evaluate(
            f"temp_low:{zone_id}", value, zone_config.temp_low_threshold, clear_above=True
        )
        changed_high, _ = alert_engine.evaluate(
            f"temp_high:{zone_id}", value, zone_config.temp_high_threshold, clear_above=False
        )
        if changed_low or changed_high:
            alert_changed = True

    elif sensor_type == "feed_weight":
        # Convert raw grams to percentage for alert evaluation
        feed_pct = (value / FEED_MAX_WEIGHT_GRAMS) * 100.0 if FEED_MAX_WEIGHT_GRAMS > 0 else 0.0
        changed, _ = alert_engine.evaluate(
            "feed_low:coop", feed_pct, FEED_LOW_THRESHOLD_PCT, clear_above=True
        )
        if changed:
            alert_changed = True
        # Broadcast feed level delta
        await notify_api({
            "type": "feed_level",
            "percentage": round(feed_pct, 1),
            "below_threshold": feed_pct < FEED_LOW_THRESHOLD_PCT,
        })

    elif sensor_type == "water_level":
        # Convert raw value to percentage
        water_pct = (value / WATER_MAX_LEVEL) * 100.0 if WATER_MAX_LEVEL > 0 else 0.0
        changed, _ = alert_engine.evaluate(
            "water_low:coop", water_pct, WATER_LOW_THRESHOLD_PCT, clear_above=True
        )
        if changed:
            alert_changed = True
        # Broadcast water level delta
        await notify_api({
            "type": "water_level",
            "percentage": round(water_pct, 1),
            "below_threshold": water_pct < WATER_LOW_THRESHOLD_PCT,
        })

    if alert_changed:
        await notify_api({
            "type": "alert_state",
            "alerts": alert_engine.get_alert_state(),
        })

    # --- Health score computation ---
    zone_cache = _zone_sensor_cache.get(zone_id, {})
    health = compute_health_score(
        zone_id,
        moisture=zone_cache.get("moisture"),
        ph=zone_cache.get("ph"),
        temperature=zone_cache.get("temperature"),
        zone_config=zone_config,
    )
    await notify_api(health)

    # --- Irrigation loop check: stop irrigation if target VWC reached or max duration exceeded ---
    irrigation_signal = irrigation_loop.check_reading(zone_id, sensor_type, value)
    if irrigation_signal:
        stopped_zone = irrigation_loop.stop()
        rule_engine.record_irrigation_complete(zone_id)
        logger.info("Irrigation loop ended for %s: %s", zone_id, irrigation_signal)
        await notify_api({
            "type": "actuator_state",
            "device": "irrigate",
            "zone_id": zone_id,
            "state": "closed",
            "reason": irrigation_signal,
        })


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
                await client.subscribe("farm/+/ack/#")
                logger.info("Subscribed to farm/+/sensors/#, farm/+/heartbeat, and farm/+/ack/#")

                async for message in client.messages:
                    topic = str(message.topic)
                    delta = None

                    if "/sensors/" in topic:
                        delta = await process_sensor_message(message.payload, db_pool)
                    elif topic.endswith("/heartbeat"):
                        delta = await process_heartbeat_message(message.payload, db_pool)
                    elif "/ack/" in topic:
                        # Parse ack payload
                        ack_data = {}
                        try:
                            ack_data = json.loads(message.payload)
                        except Exception:
                            pass

                        command_id = ack_data.get("command_id", topic.split("/")[-1])
                        node_id = ack_data.get("node_id", "")
                        status = ack_data.get("status", "confirmed")

                        # COOP-03: Signal stuck-door watchdog that ack arrived
                        if "coop" in topic:
                            mark_coop_ack_received()
                            # Broadcast confirmed door state
                            await notify_api({
                                "type": "actuator_state",
                                "device": "coop_door",
                                "zone_id": "coop",
                                "state": "confirmed",
                            })
                        else:
                            # Irrigation ack — broadcast actuator state
                            # Extract zone_id from topic: farm/{zone_id}/ack/{command_id}
                            topic_parts = topic.split("/")
                            ack_zone_id = topic_parts[1] if len(topic_parts) > 1 else ""
                            await notify_api({
                                "type": "actuator_state",
                                "device": "irrigate",
                                "zone_id": ack_zone_id,
                                "state": "confirmed",
                            })

                        delta = {
                            "type": "actuator_ack",
                            "command_id": command_id,
                            "node_id": node_id,
                            "status": status,
                        }

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
    await zone_config_store.load_from_db(db_pool)

    await asyncio.gather(
        bridge_loop(db_pool),
        coop_scheduler_loop(notify_callback=notify_api),
    )


if __name__ == "__main__":
    asyncio.run(main())
