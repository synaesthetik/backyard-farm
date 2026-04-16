"""Hub MQTT bridge — subscribes to all farm topics, processes readings,
writes to TimescaleDB, and notifies the dashboard WebSocket manager.

Pipeline per reading:
  1. Parse MQTT payload (Pydantic validation)
  2. Apply calibration offset (ZONE-03)
  3. Apply quality flag (INFRA-02, D-10, D-11)
  4. Check stuck detection (INFRA-07, D-12)
  5. INSERT into TimescaleDB sensor_readings hypertable
  6. Evaluate rules / alerts / health score (Phase 2)
  7. Phase 4: ONNX inference (AI-03) and threshold-crossing re-inference (AI-03)
  8. Broadcast delta to WebSocket clients via HTTP notify
"""
import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone

import aiomqtt
import asyncpg
from aiohttp import web
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
from flock_config import FlockConfigStore
from egg_estimator import estimate_egg_count
from production_model import (
    compute_expected_production,
    compute_age_factor,
    compute_daylight_factor,
    BREED_LAY_RATES,
)
from feed_consumption import compute_daily_feed_consumption

# Phase 4 inference imports
from inference.feature_aggregator import FeatureAggregator
from inference.inference_service import InferenceService
from inference.inference_scheduler import InferenceScheduler
from inference.maturity_tracker import MaturityTracker
from inference.ai_settings import AISettings
from inference.model_watcher import start_model_watcher

# Phase 5: ntfy push notification imports (NOTF-03)
from ntfy_settings import NtfySettings
from ntfy import send_ntfy_notification, send_ntfy_test

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

# Phase 3 flock instances
flock_config_store = FlockConfigStore()

# Phase 4 inference instances
ai_settings = AISettings()
inference_scheduler = None  # initialized in main() after db_pool
_maturity_tracker = None   # initialized in main() after db_pool

# Phase 5: ntfy settings instance (NOTF-03, D-06, D-07, D-09)
ntfy_settings = NtfySettings()

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
        # Phase 4 (AI-03): threshold crossing detected — trigger immediate AI re-inference
        # so the ONNX model re-evaluates the zone without waiting for the next scheduled cycle.
        # trigger_zone_reinference() checks AI/Rules toggle internally and is a no-op when
        # mode is "rules" or no model is loaded.
        if inference_scheduler is not None:
            asyncio.create_task(inference_scheduler.trigger_zone_reinference(zone_id))

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

    elif sensor_type == "nesting_box_weight":
        # Phase 3: per-reading egg count estimate (real-time path, D-02)
        await _evaluate_phase3_nesting_box(zone_id, value, quality_str)

    if alert_changed:
        await notify_api({
            "type": "alert_state",
            "alerts": alert_engine.get_alert_state(),
        })
        asyncio.create_task(_dispatch_ntfy_for_alerts())

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


async def _bridge_read_vwc_high_threshold(zone_id: str, db_pool: asyncpg.Pool) -> float:
    """Read vwc_high_threshold for zone from TimescaleDB. Falls back to 60.0."""
    try:
        row = await db_pool.fetchrow(
            "SELECT vwc_high_threshold FROM zone_configs WHERE zone_id = $1",
            zone_id
        )
        if row and row["vwc_high_threshold"] is not None:
            return float(row["vwc_high_threshold"])
    except Exception as e:
        logger.warning("Failed to read zone config for %s: %s", zone_id, e)
    return 60.0


async def _dispatch_ntfy_for_alerts() -> None:
    """Send ntfy notifications for current alert state (fire-and-forget, NOTF-03).

    Only called when alert state changes — not on every evaluation cycle.
    Uses asyncio.create_task() at call site to keep it non-blocking (T-05-06).
    """
    if not ntfy_settings.is_enabled():
        return
    for alert in alert_engine.get_alert_state():
        asyncio.create_task(send_ntfy_notification(ntfy_settings, alert))


async def _handle_get_ntfy_settings(request: web.Request) -> web.Response:
    """GET /internal/ntfy-settings — return current ntfy settings."""
    return web.json_response(ntfy_settings.get_all())


async def _handle_patch_ntfy_settings(request: web.Request) -> web.Response:
    """PATCH /internal/ntfy-settings — update ntfy settings fields.

    Body: JSON with any subset of {url, topic, enabled}.
    Takes effect immediately — no bridge restart required.
    """
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    allowed = {"url", "topic", "enabled"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return web.json_response({"error": "No valid fields provided"}, status=400)

    ntfy_settings.update(**fields)
    return web.json_response(ntfy_settings.get_all())


async def _handle_ntfy_test(request: web.Request) -> web.Response:
    """POST /internal/ntfy-test — send a test notification via ntfy."""
    ok, msg = await send_ntfy_test(ntfy_settings)
    if ok:
        return web.json_response({"status": "ok"})
    return web.json_response({"status": "error", "message": msg}, status=502)


async def _handle_approve(request: web.Request) -> web.Response:
    """POST /internal/recommendations/{recommendation_id}/approve

    Called by the API process to approve a recommendation.
    Runs rule_engine.approve(), opens the valve via MQTT, starts IrrigationLoop.
    """
    recommendation_id = request.match_info["recommendation_id"]
    db_pool = request.app["db_pool"]

    zone_id = rule_engine.approve(recommendation_id)
    if zone_id is None:
        return web.json_response(
            {"error": "Recommendation not found or not pending"},
            status=404
        )

    # Phase 4: record approval in maturity tracker (AI-07)
    if _maturity_tracker is not None:
        _maturity_tracker.record_approval("irrigation")
        await _maturity_tracker.persist_to_db()

    # Read zone-configured target VWC from DB (not hardcoded)
    target_vwc = await _bridge_read_vwc_high_threshold(zone_id, db_pool)

    # Open the valve via MQTT (bridge publishes the command directly)
    import uuid
    command_id = str(uuid.uuid4())
    payload = json.dumps({
        "command_id": command_id,
        "action": "open",
        "zone_id": zone_id,
    })
    try:
        async with aiomqtt.Client(
            MQTT_HOST, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASS
        ) as client:
            await client.publish(f"farm/{zone_id}/commands/irrigate", payload, qos=1)
        logger.info("Approve: valve open command published for zone %s", zone_id)
    except Exception as e:
        logger.error("Failed to publish valve open for %s: %s", zone_id, e)
        # Undo approve so recommendation is not stuck in limbo
        rule_engine.reject(recommendation_id)
        return web.json_response({"error": f"Failed to open valve: {e}"}, status=502)

    # Start sensor-feedback irrigation loop
    irrigation_loop.start(zone_id, target_vwc)

    # Broadcast updated recommendation queue to dashboard
    await notify_api({
        "type": "recommendation_queue",
        "recommendations": rule_engine.get_pending_recommendations(),
    })

    return web.json_response({"status": "approved", "zone_id": zone_id, "target_vwc": target_vwc})


async def _handle_reject(request: web.Request) -> web.Response:
    """POST /internal/recommendations/{recommendation_id}/reject

    Called by the API process to reject a recommendation.
    Runs rule_engine.reject() which starts the back-off window (AI-05).
    """
    recommendation_id = request.match_info["recommendation_id"]

    rule_engine.reject(recommendation_id)

    # Phase 4: record rejection in maturity tracker (AI-07)
    if _maturity_tracker is not None:
        _maturity_tracker.record_rejection("irrigation")
        await _maturity_tracker.persist_to_db()

    # Broadcast updated recommendation queue to dashboard
    await notify_api({
        "type": "recommendation_queue",
        "recommendations": rule_engine.get_pending_recommendations(),
    })

    return web.json_response({"status": "rejected"})


async def _handle_get_calibrations(request: web.Request) -> web.Response:
    """GET /internal/calibrations — return all calibration entries."""
    return web.json_response(calibration_store.get_all_calibrations())


async def _handle_record_calibration(request: web.Request) -> web.Response:
    """POST /internal/calibrations/{zone_id}/{sensor_type}/record

    Records a calibration event: UPSERTs with last_calibration_date = NOW().
    After recording, checks and clears any ph_calibration_overdue alert for the zone.
    Body: JSON with optional fields: offset (float), dry_value (float|null),
          wet_value (float|null), temp_coefficient (float, default 0.0).
    """
    zone_id = request.match_info["zone_id"]
    sensor_type = request.match_info["sensor_type"]
    db_pool = request.app["db_pool"]

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    offset = body.get("offset")
    if offset is None:
        return web.json_response({"error": "offset is required"}, status=400)
    try:
        offset = float(offset)
    except (TypeError, ValueError):
        return web.json_response({"error": "offset must be a number"}, status=400)

    dry_value = body.get("dry_value")
    wet_value = body.get("wet_value")
    temp_coefficient = float(body.get("temp_coefficient", 0.0))

    await calibration_store.record_calibration(
        zone_id, sensor_type, offset, db_pool,
        dry_value=dry_value,
        wet_value=wet_value,
        temp_coefficient=temp_coefficient,
    )

    # Clear ph_calibration_overdue alert if it was active (D-01)
    if sensor_type == "ph":
        alert_key = f"ph_calibration_overdue:{zone_id}"
        if alert_key in alert_engine._active_alerts:
            alert_engine.clear_alert(alert_key)
            await notify_api({
                "type": "alert_state",
                "alerts": alert_engine.get_alert_state(),
            })

    return web.json_response({"status": "recorded", "zone_id": zone_id, "sensor_type": sensor_type})


async def _handle_patch_calibration(request: web.Request) -> web.Response:
    """PATCH /internal/calibrations/{zone_id}/{sensor_type}

    Updates specific calibration fields without setting last_calibration_date.
    Body: JSON with any subset of {offset_value, dry_value, wet_value, temp_coefficient}.
    """
    zone_id = request.match_info["zone_id"]
    sensor_type = request.match_info["sensor_type"]
    db_pool = request.app["db_pool"]

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    allowed = {"offset_value", "dry_value", "wet_value", "temp_coefficient"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return web.json_response({"error": "No valid fields provided"}, status=400)

    await calibration_store.update_calibration_fields(zone_id, sensor_type, db_pool, **fields)
    return web.json_response({"status": "updated", "zone_id": zone_id, "sensor_type": sensor_type})


async def _handle_get_ai_settings(request: web.Request) -> web.Response:
    """GET /internal/ai-settings — return current AI/Rules toggle state."""
    return web.json_response(ai_settings.get_all())


async def _handle_patch_ai_settings(request: web.Request) -> web.Response:
    """PATCH /internal/ai-settings — update a single domain toggle.

    Body: {"domain": "irrigation"|"zone_health"|"flock_anomaly", "mode": "ai"|"rules"}
    Takes effect on the next inference cycle (D-06 — no restart required).
    """
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    domain = body.get("domain", "")
    mode = body.get("mode", "")

    try:
        ai_settings.set_mode(domain, mode)
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)

    return web.json_response(ai_settings.get_all())


async def _handle_get_model_maturity(request: web.Request) -> web.Response:
    """GET /internal/model-maturity — return maturity tracker state plus per-zone data maturity."""
    maturity_states = _maturity_tracker.get_all_maturity_states() if _maturity_tracker else []

    # Append per-zone data maturity from feature aggregator
    db_pool = request.app["db_pool"]
    zone_data_maturity = []
    try:
        feature_aggregator = FeatureAggregator(db_pool)
        for zone_id in zone_config_store:
            zone_maturity = await feature_aggregator.check_data_maturity(zone_id)
            zone_data_maturity.append(zone_maturity)
    except Exception as exc:
        logger.warning("Failed to fetch zone data maturity: %s", exc)

    return web.json_response({
        "domain_maturity": maturity_states,
        "zone_data_maturity": zone_data_maturity,
    })


async def run_internal_server(db_pool: asyncpg.Pool):
    """Run internal HTTP server on port 8001 for cross-process IPC.

    Exposes approve/reject recommendation endpoints so the API process
    can drive rule_engine and irrigation_loop (which live in bridge).
    Phase 4 adds AI settings and model maturity endpoints.
    Port 8001 is NOT exposed to the host in docker-compose — internal only.
    """
    app = web.Application()
    app["db_pool"] = db_pool
    app.router.add_post(
        "/internal/recommendations/{recommendation_id}/approve",
        _handle_approve
    )
    app.router.add_post(
        "/internal/recommendations/{recommendation_id}/reject",
        _handle_reject
    )
    # Phase 4: AI settings toggle and model maturity endpoints
    app.router.add_get("/internal/ai-settings", _handle_get_ai_settings)
    app.router.add_route("PATCH", "/internal/ai-settings", _handle_patch_ai_settings)
    app.router.add_get("/internal/model-maturity", _handle_get_model_maturity)
    # Phase 5: ntfy settings and test endpoints (NOTF-03)
    app.router.add_get("/internal/ntfy-settings", _handle_get_ntfy_settings)
    app.router.add_route("PATCH", "/internal/ntfy-settings", _handle_patch_ntfy_settings)
    app.router.add_post("/internal/ntfy-test", _handle_ntfy_test)
    # Phase 5: Calibration endpoints
    app.router.add_get("/internal/calibrations", _handle_get_calibrations)
    app.router.add_post(
        "/internal/calibrations/{zone_id}/{sensor_type}/record",
        _handle_record_calibration,
    )
    app.router.add_route(
        "PATCH", "/internal/calibrations/{zone_id}/{sensor_type}",
        _handle_patch_calibration,
    )
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8001)
    await site.start()
    logger.info("Bridge internal HTTP server started on port 8001")
    # Keep running forever alongside bridge_loop and coop_scheduler_loop
    await asyncio.Event().wait()


async def _evaluate_phase3_nesting_box(zone_id: str, value: float, quality_str: str):
    """Per-reading handler for nesting_box_weight sensor type (Phase 3, real-time path).

    Computes egg count estimate and hen_present from raw weight, UPSERTs today's
    egg_counts row, and broadcasts a nesting_box delta immediately.
    Quality must be GOOD to update the count.
    """
    if quality_str != "GOOD":
        return

    flock_config = flock_config_store.get()
    egg_count, hen_present = estimate_egg_count(value, flock_config)
    updated_at = datetime.now(timezone.utc)

    await notify_api({
        "type": "nesting_box",
        "estimated_count": egg_count,
        "hen_present": hen_present,
        "raw_weight_grams": value,
        "updated_at": updated_at.isoformat(),
    })


async def periodic_calibration_check(db_pool: asyncpg.Pool):
    """Hourly check: fire/clear ph_calibration_overdue alerts per zone (D-01)."""
    while True:
        await asyncio.sleep(60 * 60)  # 1 hour
        try:
            rows = await db_pool.fetch(
                "SELECT zone_id FROM calibration_offsets WHERE sensor_type = 'ph'"
            )
            alert_changed = False
            for row in rows:
                zone_id = row["zone_id"]
                alert_key = f"ph_calibration_overdue:{zone_id}"
                is_overdue = calibration_store.is_overdue(zone_id, "ph")
                was_active = alert_key in alert_engine._active_alerts
                if is_overdue and not was_active:
                    alert_engine.set_alert(alert_key)
                    alert_changed = True
                elif not is_overdue and was_active:
                    alert_engine.clear_alert(alert_key)
                    alert_changed = True
            if alert_changed:
                await notify_api({
                    "type": "alert_state",
                    "alerts": alert_engine.get_alert_state(),
                })
                asyncio.create_task(_dispatch_ntfy_for_alerts())
        except Exception as e:
            logger.error("periodic_calibration_check error: %s", e)


async def periodic_flock_loop(db_pool: asyncpg.Pool):
    """Run every 30 minutes: estimate egg count from latest nesting box reading,
    UPSERT egg_counts, and evaluate production drop alert (Phase 3, D-02).
    """
    while True:
        await asyncio.sleep(30 * 60)
        try:
            flock_config = flock_config_store.get()

            # Query latest GOOD nesting_box_weight from last 35 minutes
            row = await db_pool.fetchrow(
                """
                SELECT value FROM sensor_readings
                WHERE zone_id = 'coop'
                  AND sensor_type = 'nesting_box_weight'
                  AND quality = 'GOOD'
                  AND time > NOW() - INTERVAL '35 minutes'
                ORDER BY time DESC
                LIMIT 1
                """
            )

            if row is not None:
                raw_weight = float(row["value"])
                egg_count, hen_present = estimate_egg_count(raw_weight, flock_config)
                today = datetime.now(timezone.utc).date()
                updated_at = datetime.now(timezone.utc)

                await db_pool.execute(
                    """
                    INSERT INTO egg_counts (count_date, estimated_count, raw_weight_grams, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (count_date) DO UPDATE
                      SET estimated_count = EXCLUDED.estimated_count,
                          raw_weight_grams = EXCLUDED.raw_weight_grams,
                          updated_at = EXCLUDED.updated_at
                    """,
                    today, egg_count, raw_weight, updated_at,
                )

                await notify_api({
                    "type": "nesting_box",
                    "estimated_count": egg_count,
                    "hen_present": hen_present,
                    "raw_weight_grams": raw_weight,
                    "updated_at": updated_at.isoformat(),
                })

            # Evaluate production drop alert — skip if fewer than 3 days of data (Pitfall 4 guard)
            rows = await db_pool.fetch(
                """
                SELECT estimated_count FROM egg_counts
                ORDER BY count_date DESC
                LIMIT 3
                """
            )

            if len(rows) < 3:
                logger.debug("Fewer than 3 egg_count records — skipping production drop alert")
            else:
                rolling_avg = sum(r["estimated_count"] for r in rows) / 3.0
                today_date = datetime.now(timezone.utc).date()
                age_factor = compute_age_factor(flock_config.hatch_date, today=today_date)
                daylight_factor = compute_daylight_factor(
                    lat=flock_config.latitude,
                    lon=flock_config.longitude,
                    today=today_date,
                    supplemental_lighting=flock_config.supplemental_lighting,
                )
                lay_rate = (
                    flock_config.lay_rate_override
                    if flock_config.lay_rate_override is not None
                    else BREED_LAY_RATES.get(flock_config.breed, 0.75) or 0.75
                )
                expected = compute_expected_production(
                    flock_size=flock_config.flock_size,
                    lay_rate=lay_rate,
                    age_factor=age_factor,
                    daylight_factor=daylight_factor,
                )

                if expected > 0:
                    ratio_pct = (rolling_avg / expected) * 100.0
                    changed, _ = alert_engine.evaluate(
                        "production_drop:coop", ratio_pct, 75.0, clear_above=True
                    )
                    if changed:
                        await notify_api({
                            "type": "alert_state",
                            "alerts": alert_engine.get_alert_state(),
                        })
                        asyncio.create_task(_dispatch_ntfy_for_alerts())

        except Exception as e:
            logger.error("periodic_flock_loop error: %s", e)


async def daily_feed_loop(db_pool: asyncpg.Pool):
    """Run daily at midnight UTC: compute feed consumption delta,
    INSERT into feed_daily_consumption, evaluate feed_consumption_drop alert.
    """
    from datetime import timedelta

    while True:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sleep_seconds = (next_midnight - now).total_seconds()
        await asyncio.sleep(sleep_seconds)

        try:
            yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)

            # Query first and last feed_weight readings for yesterday
            first_row = await db_pool.fetchrow(
                """
                SELECT value FROM sensor_readings
                WHERE zone_id = 'coop'
                  AND sensor_type = 'feed_weight'
                  AND quality = 'GOOD'
                  AND time::date = $1
                ORDER BY time ASC
                LIMIT 1
                """,
                yesterday,
            )
            last_row = await db_pool.fetchrow(
                """
                SELECT value FROM sensor_readings
                WHERE zone_id = 'coop'
                  AND sensor_type = 'feed_weight'
                  AND quality = 'GOOD'
                  AND time::date = $1
                ORDER BY time DESC
                LIMIT 1
                """,
                yesterday,
            )

            if first_row is None or last_row is None:
                logger.info("No feed_weight readings for %s — skipping daily_feed_loop", yesterday)
                continue

            consumption_grams, refill_detected = compute_daily_feed_consumption(
                start_weight=float(first_row["value"]),
                end_weight=float(last_row["value"]),
            )

            updated_at = datetime.now(timezone.utc)
            await db_pool.execute(
                """
                INSERT INTO feed_daily_consumption
                  (consumption_date, consumption_grams, refill_detected, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (consumption_date) DO UPDATE
                  SET consumption_grams = EXCLUDED.consumption_grams,
                      refill_detected = EXCLUDED.refill_detected,
                      updated_at = EXCLUDED.updated_at
                """,
                yesterday, consumption_grams, refill_detected, updated_at,
            )

            # Query last 7 days of consumption (exclude refill/null days for trend)
            rows = await db_pool.fetch(
                """
                SELECT consumption_grams FROM feed_daily_consumption
                WHERE refill_detected = FALSE
                  AND consumption_grams IS NOT NULL
                ORDER BY consumption_date DESC
                LIMIT 7
                """
            )

            values = [float(r["consumption_grams"]) for r in rows]
            # weekly sparkline oldest-first, pad with 0 for missing days
            weekly = list(reversed(values)) + [0.0] * max(0, 7 - len(values))
            rate = consumption_grams if consumption_grams is not None else (values[0] if values else 0.0)

            await notify_api({
                "type": "feed_consumption",
                "rate_grams_per_day": rate,
                "weekly": weekly[:7],
            })

            # Evaluate feed_consumption_drop alert — skip if fewer than 3 data points (Pitfall 4 guard)
            if len(values) < 3:
                logger.debug("Fewer than 3 feed consumption records — skipping alert evaluation")
                continue

            seven_day_avg = sum(values) / len(values)
            if seven_day_avg > 0 and consumption_grams is not None:
                deviation_pct = ((seven_day_avg - consumption_grams) / seven_day_avg) * 100.0
                changed, _ = alert_engine.evaluate(
                    "feed_consumption_drop:coop", deviation_pct, 30.0, clear_above=False
                )
                if changed:
                    await notify_api({
                        "type": "alert_state",
                        "alerts": alert_engine.get_alert_state(),
                    })
                    asyncio.create_task(_dispatch_ntfy_for_alerts())

        except Exception as e:
            logger.error("daily_feed_loop error: %s", e)


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
    await flock_config_store.load_from_db(db_pool)

    # Phase 4: Initialize inference components
    global inference_scheduler, _maturity_tracker
    feature_aggregator = FeatureAggregator(db_pool)
    _maturity_tracker = MaturityTracker(db_pool)
    await _maturity_tracker.ensure_table()
    await _maturity_tracker.load_from_db()

    inference_services = {
        "zone_health": InferenceService("zone_health"),
        "irrigation": InferenceService("irrigation"),
        "flock_anomaly": InferenceService("flock_anomaly"),
    }

    inference_scheduler = InferenceScheduler(
        db_pool=db_pool,
        feature_aggregator=feature_aggregator,
        inference_services=inference_services,
        maturity_tracker=_maturity_tracker,
        ai_settings=ai_settings,
        zone_config_store=zone_config_store,
        notify_callback=notify_api,
    )
    inference_scheduler.start()

    # Start model file watcher (D-09) — daemon thread, safe alongside asyncio
    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(models_dir, exist_ok=True)
    start_model_watcher(models_dir, inference_services)
    logger.info("Phase 4 inference components initialized")

    # APScheduler runs cooperatively in the event loop (04-RESEARCH.md Pattern 4).
    # No new coroutine needed in gather() — scheduler attaches to existing loop.
    await asyncio.gather(
        bridge_loop(db_pool),
        coop_scheduler_loop(notify_callback=notify_api),
        run_internal_server(db_pool),
        periodic_flock_loop(db_pool),
        daily_feed_loop(db_pool),
        periodic_calibration_check(db_pool),
    )


if __name__ == "__main__":
    asyncio.run(main())
