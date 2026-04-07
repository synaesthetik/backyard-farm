"""WebSocket connection manager for dashboard real-time updates (D-16).

Manages connected WebSocket clients. Receives deltas from bridge via
internal HTTP endpoint and broadcasts to all connected clients.
"""
import json
import logging
import asyncio
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._zone_states: dict[str, dict] = {}
        self._node_states: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send full snapshot on connect (D-16)
        snapshot = {
            "type": "snapshot",
            "zones": self._zone_states,
            "nodes": self._node_states,
        }
        await websocket.send_json(snapshot)
        logger.info("WebSocket client connected (%d total)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(self.active_connections))

    def update_state(self, delta: dict):
        """Update internal state cache from bridge delta."""
        if delta.get("type") == "sensor_update":
            zone_id = delta["zone_id"]
            if zone_id not in self._zone_states:
                self._zone_states[zone_id] = {}
            self._zone_states[zone_id][delta["sensor_type"]] = {
                "value": delta["value"],
                "quality": delta["quality"],
                "stuck": delta["stuck"],
                "received_at": delta["received_at"],
            }
        elif delta.get("type") == "heartbeat":
            node_id = delta["node_id"]
            self._node_states[node_id] = {
                "ts": delta["ts"],
                "uptime_seconds": delta["uptime_seconds"],
                "last_seen": delta["ts"],
            }

    async def broadcast(self, delta: dict):
        """Broadcast delta to all connected WebSocket clients."""
        self.update_state(delta)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(delta)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)
