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
    # Phase 2 additions
    command_id: Optional[str] = None
    action: Optional[str] = None
    command_type: Optional[str] = None
    state: Optional[str] = None
    device: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    deep_link: Optional[str] = None
    count: Optional[int] = None
    alerts: Optional[list] = None
    recommendations: Optional[list] = None
    recommendation_id: Optional[str] = None
    rec_type: Optional[str] = None
    action_description: Optional[str] = None
    sensor_reading: Optional[str] = None
    explanation: Optional[str] = None
    score: Optional[str] = None
    contributing_sensors: Optional[list] = None
    percentage: Optional[float] = None
    below_threshold: Optional[bool] = None
    status: Optional[str] = None
