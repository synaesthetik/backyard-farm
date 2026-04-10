"""Pydantic models for MQTT payloads and internal data."""
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


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


# Phase 2 models

class ActuatorCommand(BaseModel):
    command_id: str
    node_id: str
    command_type: str  # "irrigate" | "coop_door"
    action: str        # "open" | "close"
    zone_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActuatorAck(BaseModel):
    command_id: str
    node_id: str
    status: str  # "confirmed" | "failed"
    ts: datetime


class RecommendationModel(BaseModel):
    recommendation_id: str
    zone_id: str
    rec_type: str          # "irrigate"
    action_description: str
    sensor_reading: str
    explanation: str
    status: str = "pending"  # "pending" | "approved" | "rejected"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertModel(BaseModel):
    key: str               # e.g. "moisture_low:zone-01"
    severity: str          # "P0" | "P1"
    message: str
    deep_link: str         # e.g. "/zones/zone-01"
    count: int = 1
    fired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
