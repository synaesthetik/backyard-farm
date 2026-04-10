"""Coop door astronomical clock scheduler (COOP-01, COOP-02, COOP-03).

Calculates daily sunrise/sunset from configured lat/long using astral 3.2.
Schedules coop door open at sunrise + offset and close at sunset + offset.
Hard time limit backstop: force-close no later than COOP_HARD_CLOSE_HOUR.

COOP-03: _stuck_door_watchdog fires a P0 stuck_door alert via notify_callback
if no ack arrives within 60 seconds of a command.

Runs as asyncio.create_task alongside bridge_loop in main().
"""
import asyncio
import json
import logging
import os
from datetime import date, datetime, timezone, timedelta

from astral import LocationInfo
from astral.sun import sun

logger = logging.getLogger(__name__)

LAT = float(os.getenv("HUB_LATITUDE", "37.7749"))
LON = float(os.getenv("HUB_LONGITUDE", "-122.4194"))
OPEN_OFFSET = int(os.getenv("COOP_OPEN_OFFSET_MINUTES", "0"))
CLOSE_OFFSET = int(os.getenv("COOP_CLOSE_OFFSET_MINUTES", "0"))
HARD_CLOSE_HOUR = int(os.getenv("COOP_HARD_CLOSE_HOUR", "21"))
STUCK_DOOR_TIMEOUT_SECONDS = int(os.getenv("STUCK_DOOR_TIMEOUT_SECONDS", "60"))

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_BRIDGE_USER", "hub-bridge")
MQTT_PASS = os.getenv("MQTT_BRIDGE_PASS", "")

# Module-level flag set by bridge when a coop ack arrives.
# The watchdog checks this to decide whether to fire the stuck alert.
_coop_ack_received = asyncio.Event()


def get_today_schedule() -> dict:
    """Calculate today's coop door open/close times.

    Returns:
        {"open_at": datetime (UTC), "close_at": datetime (UTC)}
    """
    location = LocationInfo(latitude=LAT, longitude=LON)
    s = sun(location.observer, date=date.today(), tzinfo=timezone.utc)

    open_time = s["sunrise"] + timedelta(minutes=OPEN_OFFSET)
    close_time = s["sunset"] + timedelta(minutes=CLOSE_OFFSET)

    # COOP-02: hard close backstop -- no later than HARD_CLOSE_HOUR UTC
    today = datetime.now(timezone.utc).date()
    hard_close = datetime(today.year, today.month, today.day,
                          HARD_CLOSE_HOUR, 0, 0, tzinfo=timezone.utc)
    close_time = min(close_time, hard_close)

    return {"open_at": open_time, "close_at": close_time}


def mark_coop_ack_received():
    """Called by bridge when a coop door ack arrives via MQTT."""
    _coop_ack_received.set()


async def _stuck_door_watchdog(notify_callback):
    """COOP-03: Wait up to STUCK_DOOR_TIMEOUT_SECONDS for coop ack.

    If no ack arrives, fire a stuck_door:coop P0 alert by calling
    notify_callback with an alert_state delta. This broadcasts the
    alert to all connected dashboard clients via WebSocket.
    """
    _coop_ack_received.clear()
    try:
        await asyncio.wait_for(
            _coop_ack_received.wait(),
            timeout=STUCK_DOOR_TIMEOUT_SECONDS
        )
        logger.info("Coop door ack received within timeout")
    except asyncio.TimeoutError:
        logger.warning("Coop door stuck -- no ack within %d seconds (COOP-03)",
                        STUCK_DOOR_TIMEOUT_SECONDS)
        if notify_callback:
            # Fire P0 stuck_door alert directly via notify_callback.
            # This bypasses alert_engine (which lives in the bridge process)
            # because the watchdog needs to broadcast immediately.
            await notify_callback({
                "type": "alert_state",
                "alerts": [{
                    "key": "stuck_door:coop",
                    "severity": "P0",
                    "message": "Coop door stuck",
                    "deep_link": "/coop",
                    "count": 1,
                }],
                "set_stuck_door": True,  # Signal bridge to also call alert_engine.set_alert
            })


async def publish_coop_command(action: str, notify_callback=None):
    """Publish a coop door command via MQTT and start stuck-door watchdog."""
    import aiomqtt
    import uuid
    command_id = str(uuid.uuid4())
    payload = json.dumps({
        "command_id": command_id,
        "action": action,
        "zone_id": "coop",
    })
    try:
        async with aiomqtt.Client(
            MQTT_HOST, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASS
        ) as client:
            await client.publish("farm/coop/commands/coop_door", payload, qos=1)
        logger.info("Coop door command published: %s (command_id=%s)", action, command_id)

        # Broadcast moving state
        if notify_callback:
            await notify_callback({
                "type": "actuator_state",
                "device": "coop_door",
                "state": "moving",
            })

        # COOP-03: Start stuck-door watchdog (runs in background)
        asyncio.create_task(_stuck_door_watchdog(notify_callback))

    except Exception as e:
        logger.error("Failed to publish coop command: %s", e)


async def coop_scheduler_loop(notify_callback=None):
    """Main scheduler loop. Runs daily: calculates schedule, sleeps until open/close times.

    Args:
        notify_callback: async function to broadcast deltas (e.g., notify_api)
    """
    while True:
        try:
            schedule = get_today_schedule()
            now = datetime.now(timezone.utc)

            logger.info("Coop schedule: open at %s, close at %s",
                        schedule["open_at"].strftime("%H:%M UTC"),
                        schedule["close_at"].strftime("%H:%M UTC"))

            # Broadcast schedule to dashboard
            if notify_callback:
                await notify_callback({
                    "type": "coop_schedule",
                    "schedule": {
                        "open_at": schedule["open_at"].isoformat(),
                        "close_at": schedule["close_at"].isoformat(),
                    },
                })

            # Wait for open time
            if now < schedule["open_at"]:
                wait_seconds = (schedule["open_at"] - now).total_seconds()
                logger.info("Waiting %.0f seconds until coop open", wait_seconds)
                await asyncio.sleep(wait_seconds)
                await publish_coop_command("open", notify_callback)

            # Wait for close time
            now = datetime.now(timezone.utc)
            if now < schedule["close_at"]:
                wait_seconds = (schedule["close_at"] - now).total_seconds()
                logger.info("Waiting %.0f seconds until coop close", wait_seconds)
                await asyncio.sleep(wait_seconds)
                await publish_coop_command("close", notify_callback)

            # Sleep until midnight to recalculate
            tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
            wait_seconds = (tomorrow - datetime.now(timezone.utc)).total_seconds()
            logger.info("Coop schedule complete for today. Sleeping until midnight (%.0fs)", wait_seconds)
            await asyncio.sleep(max(wait_seconds, 60))

        except asyncio.CancelledError:
            logger.info("Coop scheduler cancelled")
            raise
        except Exception as e:
            logger.error("Coop scheduler error: %s -- retrying in 60s", e)
            await asyncio.sleep(60)
