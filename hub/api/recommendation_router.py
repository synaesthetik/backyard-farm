"""Recommendation management endpoints (AI-01 approve/reject, IRRIG-05).

POST /api/recommendations/{id}/approve -- proxies to bridge internal server
POST /api/recommendations/{id}/reject  -- proxies to bridge internal server

The rule_engine and irrigation_loop live in the bridge process (separate Docker
container). This router proxies approve/reject HTTP calls to the bridge's
internal HTTP server at BRIDGE_INTERNAL_URL (default: http://bridge:8001).
The bridge owns the state mutation; this router owns the HTTP interface.
"""
import logging
import os
import aiohttp
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

BRIDGE_INTERNAL_URL = os.getenv("BRIDGE_INTERNAL_URL", "http://bridge:8001")

# Kept for interface compatibility — main.py still calls init() at startup.
# _notify_callback, _ws_manager, _db_pool are still used; _rule_engine and
# _irrigation_loop are unused (bridge owns them) but accepted to avoid main.py changes.
_rule_engine = None
_irrigation_loop = None
_notify_callback = None
_ws_manager = None
_db_pool = None


def init(rule_engine, irrigation_loop, notify_callback, ws_manager, db_pool):
    """Called from main.py to inject dependencies. rule_engine and irrigation_loop
    are always None in the API process — the bridge owns these instances."""
    global _rule_engine, _irrigation_loop, _notify_callback, _ws_manager, _db_pool
    _rule_engine = rule_engine
    _irrigation_loop = irrigation_loop
    _notify_callback = notify_callback
    _ws_manager = ws_manager
    _db_pool = db_pool


@router.post("/api/recommendations/{recommendation_id}/approve")
async def approve_recommendation(recommendation_id: str):
    """Approve a recommendation. Proxies to bridge internal server.

    Bridge handles: rule_engine.approve(), valve open via MQTT, IrrigationLoop.start().
    Returns 200 on success; forwards 404/409/502 from bridge on error.
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/recommendations/{recommendation_id}/approve"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                body = await resp.json()
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail=body.get("error", str(body)))
                return body
    except aiohttp.ClientConnectorError as e:
        logger.error("Cannot reach bridge internal server at %s: %s", url, e)
        raise HTTPException(status_code=503, detail="Bridge unreachable — recommendation service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error proxying approve to bridge: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/recommendations/{recommendation_id}/reject")
async def reject_recommendation(recommendation_id: str):
    """Reject a recommendation. Proxies to bridge internal server.

    Bridge handles: rule_engine.reject() which starts back-off window (AI-05).
    """
    url = f"{BRIDGE_INTERNAL_URL}/internal/recommendations/{recommendation_id}/reject"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                body = await resp.json()
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail=body.get("error", str(body)))
                return body
    except aiohttp.ClientConnectorError as e:
        logger.error("Cannot reach bridge internal server at %s: %s", url, e)
        raise HTTPException(status_code=503, detail="Bridge unreachable — recommendation service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error proxying reject to bridge: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
