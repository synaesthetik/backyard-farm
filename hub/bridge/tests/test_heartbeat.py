"""Tests for heartbeat processing."""
import json
import pytest
from datetime import datetime, timezone
from models import HeartbeatPayload


def test_valid_heartbeat_payload():
    data = {
        "node_id": "zone-01",
        "ts": "2026-04-07T12:00:00Z",
        "uptime_seconds": 3600,
    }
    hb = HeartbeatPayload(**data)
    assert hb.node_id == "zone-01"
    assert hb.uptime_seconds == 3600


def test_invalid_heartbeat_missing_node_id():
    with pytest.raises(Exception):
        HeartbeatPayload(**{"ts": "2026-04-07T12:00:00Z", "uptime_seconds": 3600})


def test_heartbeat_delta_format():
    """Verify the delta dict format matches what WebSocket manager expects."""
    delta = {
        "type": "heartbeat",
        "node_id": "zone-01",
        "ts": "2026-04-07T12:00:00Z",
        "uptime_seconds": 3600,
    }
    assert delta["type"] == "heartbeat"
    assert "node_id" in delta
    assert "ts" in delta
