"""Pydantic models for API endpoints."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    service: str


class NotifyPayload(BaseModel):
    type: str
    zone_id: Optional[str] = None
    sensor_type: Optional[str] = None
    value: Optional[float] = None
    quality: Optional[str] = None
    stuck: Optional[bool] = None
    received_at: Optional[str] = None
    node_id: Optional[str] = None
    ts: Optional[str] = None
    uptime_seconds: Optional[int] = None
