"""Recommendation management endpoints (AI-01 approve/reject, IRRIG-05).

POST /api/recommendations/{id}/approve -- opens valve AND starts sensor-feedback irrigation loop
POST /api/recommendations/{id}/reject -- starts back-off window
"""
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

# Injected by main.py at startup
_rule_engine = None
_irrigation_loop = None
_notify_callback = None
_ws_manager = None
_db_pool = None  # asyncpg pool for reading zone config


def init(rule_engine, irrigation_loop, notify_callback, ws_manager, db_pool):
    """Called from main.py to inject dependencies."""
    global _rule_engine, _irrigation_loop, _notify_callback, _ws_manager, _db_pool
    _rule_engine = rule_engine
    _irrigation_loop = irrigation_loop
    _notify_callback = notify_callback
    _ws_manager = ws_manager
    _db_pool = db_pool


async def _read_vwc_high_threshold(zone_id: str) -> float:
    """Read vwc_high_threshold from zone_config table via asyncpg.

    Falls back to 60.0 if no config found or DB unavailable.
    This avoids hardcoding target_vwc -- the zone's configured
    vwc_high_threshold is the correct irrigation target.
    """
    if not _db_pool:
        logger.warning("No DB pool available, using default vwc_high_threshold=60.0")
        return 60.0
    try:
        row = await _db_pool.fetchrow(
            "SELECT vwc_high_threshold FROM zone_configs WHERE zone_id = $1",
            zone_id
        )
        if row and row["vwc_high_threshold"] is not None:
            return float(row["vwc_high_threshold"])
    except Exception as e:
        logger.warning("Failed to read zone config for %s: %s", zone_id, e)
    return 60.0


@router.post("/api/recommendations/{recommendation_id}/approve")
async def approve_recommendation(recommendation_id: str):
    """Approve a recommendation. For irrigation: opens the valve AND starts sensor-feedback loop."""
    if not _rule_engine:
        raise HTTPException(status_code=503, detail="Rule engine not initialized")

    zone_id = _rule_engine.approve(recommendation_id)
    if zone_id is None:
        raise HTTPException(status_code=404, detail="Recommendation not found or not pending")

    # IRRIG-02: Check single-zone invariant
    import actuator_router
    if actuator_router.active_irrigation_zone is not None:
        raise HTTPException(status_code=409, detail="Another zone is already irrigating.")

    # Read the zone's vwc_high_threshold from DB as irrigation target
    target_vwc = await _read_vwc_high_threshold(zone_id)

    # IRRIG-05: FIRST open the valve by calling actuator_router's shared command function.
    # This sends the MQTT command and waits for ack. The valve MUST actually open.
    try:
        from actuator_router import _send_irrigation_command
        await _send_irrigation_command(zone_id, "open")
    except Exception as e:
        logger.error("Failed to open valve for %s: %s", zone_id, e)
        raise HTTPException(status_code=502, detail=f"Failed to open valve: {e}")

    # THEN start the sensor-feedback irrigation loop to monitor VWC
    if _irrigation_loop:
        _irrigation_loop.start(zone_id, target_vwc)

    # Broadcast updated recommendation queue
    if _notify_callback and _rule_engine:
        await _notify_callback({
            "type": "recommendation_queue",
            "recommendations": _rule_engine.get_pending_recommendations(),
        })

    return {"status": "approved", "zone_id": zone_id, "target_vwc": target_vwc}


@router.post("/api/recommendations/{recommendation_id}/reject")
async def reject_recommendation(recommendation_id: str):
    """Reject a recommendation. Starts back-off window (AI-05)."""
    if not _rule_engine:
        raise HTTPException(status_code=503, detail="Rule engine not initialized")

    _rule_engine.reject(recommendation_id)

    # Broadcast updated recommendation queue
    if _notify_callback and _rule_engine:
        await _notify_callback({
            "type": "recommendation_queue",
            "recommendations": _rule_engine.get_pending_recommendations(),
        })

    return {"status": "rejected"}
