"""Farm Dashboard API — FastAPI with WebSocket support.

Serves REST endpoints and manages WebSocket connections for the dashboard.
Bridge service sends deltas via internal /internal/notify endpoint.
"""
import asyncio
import logging
import os

import asyncpg
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ws_manager import WebSocketManager
from models import HealthResponse, NotifyPayload
from actuator_router import router as actuator_router
from history_router import router as history_router
from recommendation_router import router as recommendation_router
import recommendation_router as rec_router_module
import flock_router
from inference_settings_router import router as inference_settings_router
from calibration_router import router as calibration_router
from ntfy_router import router as ntfy_router
from storage_router import router as storage_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Farm Dashboard API", version="0.1.0")
ws_manager = WebSocketManager()

app.include_router(actuator_router)
app.include_router(history_router)
app.include_router(recommendation_router)
app.include_router(flock_router.router)
app.include_router(inference_settings_router)
app.include_router(calibration_router)
app.include_router(ntfy_router)
app.include_router(storage_router)

_db_pool = None


def get_db_pool():
    """Return the shared asyncpg connection pool."""
    return _db_pool


@app.on_event("startup")
async def startup():
    global _db_pool
    _db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "timescaledb"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "farm"),
        password=os.getenv("POSTGRES_PASSWORD", "farm_local_dev"),
        database=os.getenv("POSTGRES_DB", "farmdb"),
        min_size=2,
        max_size=5,
    )
    logger.info("API DB pool connected")

    # Inject dependencies into recommendation router
    # rule_engine and irrigation_loop are owned by the bridge process;
    # the API process receives deltas via /internal/notify and does not
    # need direct engine references for history/recommendation endpoints.
    # The recommendation_router.init() call wires in the DB pool so
    # approve_recommendation() can read zone config for target VWC.
    rec_router_module.init(
        rule_engine=None,
        irrigation_loop=None,
        notify_callback=_notify_ws,
        ws_manager=ws_manager,
        db_pool=_db_pool,
    )


async def _notify_ws(delta: dict):
    """Broadcast a delta directly to WebSocket clients (used by recommendation_router)."""
    await ws_manager.broadcast(delta)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return {"status": "ok", "service": "farm-api"}


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client does not send data
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/internal/notify")
async def internal_notify(payload: NotifyPayload):
    """Internal endpoint - bridge sends sensor/heartbeat/ack deltas here."""
    delta = payload.model_dump(exclude_none=True)
    if delta.get("type") == "actuator_ack":
        from actuator_router import resolve_ack
        resolve_ack(delta.get("command_id", ""))
        # Broadcast actuator state update to WebSocket clients
        # The actual state change is broadcast separately by the engine
    else:
        await ws_manager.broadcast(delta)
    return {"status": "ok"}
