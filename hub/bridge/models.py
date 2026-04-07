"""Pydantic models for MQTT payloads and internal data."""
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class QualityFlag(str, Enum):
    GOOD = "GOOD"
    SUSPECT = "SUSPECT"
    BAD = "BAD"


class SensorPayload(BaseModel):
    zone_id: str
    sensor_type: str
    value: float
    ts: datetime
    node_id: str


class HeartbeatPayload(BaseModel):
    node_id: str
    ts: datetime
    uptime_seconds: int


class ProcessedReading(BaseModel):
    zone_id: str
    sensor_type: str
    value: float
    raw_value: float
    quality: QualityFlag
    stuck: bool = False
    calibration_applied: bool = False
    ts: datetime
    received_at: datetime = Field(default_factory=datetime.utcnow)
    node_id: str
