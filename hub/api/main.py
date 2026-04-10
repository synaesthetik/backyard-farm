"""Farm Dashboard API — FastAPI with WebSocket support.

Serves REST endpoints and manages WebSocket connections for the dashboard.
Bridge service sends deltas via internal /internal/notify endpoint.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ws_manager import WebSocketManager
from models import HealthResponse, NotifyPayload
from actuator_router import router as actuator_router

app = FastAPI(title="Farm Dashboard API", version="0.1.0")
ws_manager = WebSocketManager()
app.include_router(actuator_router)


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
