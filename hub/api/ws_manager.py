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
        self._alert_state: list[dict] = []
        self._recommendation_queue: list[dict] = []
        self._actuator_states: dict[str, str] = {}  # "irrigation:zone-01" -> "open"
        self._zone_health_scores: dict[str, dict] = {}
        self._feed_level: dict | None = None
        self._water_level: dict | None = None
        self._coop_schedule: dict | None = None
        # Phase 3 flock state
        self._egg_count: dict | None = None
        self._feed_consumption: dict | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send full snapshot on connect (D-16)
        snapshot = {
            "type": "snapshot",
            "zones": self._zone_states,
            "nodes": self._node_states,
            "alerts": self._alert_state,
            "recommendations": self._recommendation_queue,
            "actuator_states": self._actuator_states,
            "zone_health_scores": self._zone_health_scores,
            "feed_level": self._feed_level,
            "water_level": self._water_level,
            "coop_schedule": self._coop_schedule,
            "egg_count": self._egg_count,
            "feed_consumption": self._feed_consumption,
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
        elif delta.get("type") == "alert_state":
            self._alert_state = delta.get("alerts", [])
        elif delta.get("type") == "recommendation_queue":
            self._recommendation_queue = delta.get("recommendations", [])
        elif delta.get("type") == "actuator_state":
            device = delta.get("device", "")
            zone_id = delta.get("zone_id", "")
            key = f"{device}:{zone_id}" if zone_id else device
            self._actuator_states[key] = delta.get("state", "")
        elif delta.get("type") == "zone_health_score":
            zone_id = delta.get("zone_id", "")
            self._zone_health_scores[zone_id] = {
                "score": delta.get("score", "green"),
                "contributing_sensors": delta.get("contributing_sensors", []),
            }
        elif delta.get("type") == "feed_level":
            self._feed_level = {"percentage": delta["percentage"], "below_threshold": delta["below_threshold"]}
        elif delta.get("type") == "water_level":
            self._water_level = {"percentage": delta["percentage"], "below_threshold": delta["below_threshold"]}
        elif delta.get("type") == "coop_schedule":
            self._coop_schedule = delta.get("schedule")
        elif delta.get("type") == "nesting_box":
            import datetime
            self._egg_count = {
                "today": delta.get("today", datetime.date.today().isoformat()),
                "hen_present": delta.get("hen_present"),
                "raw_weight_grams": delta.get("raw_weight_grams"),
                "updated_at": delta.get("updated_at"),
            }
        elif delta.get("type") == "feed_consumption":
            self._feed_consumption = {
                "rate_grams_per_day": delta.get("rate_grams_per_day"),
                "weekly": delta.get("weekly"),
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
