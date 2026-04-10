"""Threshold-based recommendation engine (AI-02).

Evaluates zone sensor readings against configured thresholds.
Generates irrigation recommendations when VWC drops below zone's low threshold.
Enforces deduplication (AI-04), rejection back-off (AI-05), and cool-down (IRRIG-06).
"""
import os
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

BACKOFF_MINUTES = int(os.getenv("RECOMMENDATION_BACKOFF_MINUTES", "60"))
COOLDOWN_MINUTES = int(os.getenv("IRRIGATION_COOLDOWN_MINUTES", "120"))


@dataclass
class RecommendationState:
    recommendation_id: str
    zone_id: str
    rec_type: str
    status: str  # "pending" | "approved" | "rejected"
    created_at: datetime
    rejected_at: Optional[datetime] = None


class RuleEngine:
    def __init__(self):
        self._recommendations: dict[str, RecommendationState] = {}  # key: "{zone_id}:{rec_type}"
        self._last_irrigated: dict[str, datetime] = {}  # zone_id -> datetime

    def evaluate_zone(self, zone_id: str, sensor_type: str, value: float,
                      zone_config) -> Optional[dict]:
        """Evaluate a sensor reading and return a recommendation dict or None.

        zone_config must have: vwc_low_threshold, vwc_high_threshold attributes.
        """
        if sensor_type != "moisture":
            return None

        low_threshold = zone_config.vwc_low_threshold
        if value >= low_threshold:
            return None

        key = f"{zone_id}:irrigate"
        existing = self._recommendations.get(key)

        # AI-04: suppress if pending recommendation exists
        if existing and existing.status == "pending":
            return None

        # AI-05: suppress if in rejection back-off window
        if existing and existing.status == "rejected" and existing.rejected_at:
            elapsed_min = (datetime.now(timezone.utc) - existing.rejected_at).total_seconds() / 60
            if elapsed_min < BACKOFF_MINUTES:
                return None

        # IRRIG-06: suppress if in cool-down window after recent irrigation
        last_irrigated = self._last_irrigated.get(zone_id)
        if last_irrigated:
            elapsed_min = (datetime.now(timezone.utc) - last_irrigated).total_seconds() / 60
            if elapsed_min < COOLDOWN_MINUTES:
                return None

        # Emit new recommendation
        rec_id = str(uuid.uuid4())
        self._recommendations[key] = RecommendationState(
            recommendation_id=rec_id,
            zone_id=zone_id,
            rec_type="irrigate",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

        high_threshold = zone_config.vwc_high_threshold
        return {
            "recommendation_id": rec_id,
            "zone_id": zone_id,
            "rec_type": "irrigate",
            "action_description": f"Irrigate {zone_id}",
            "sensor_reading": f"Moisture: {value:.1f}% VWC (target range: {low_threshold:.0f}\u2013{high_threshold:.0f}%)",
            "explanation": "Below low threshold",
        }

    def approve(self, recommendation_id: str) -> Optional[str]:
        """Mark recommendation as approved. Returns zone_id if found."""
        for key, rec in self._recommendations.items():
            if rec.recommendation_id == recommendation_id and rec.status == "pending":
                rec.status = "approved"
                return rec.zone_id
        return None

    def reject(self, recommendation_id: str):
        """Mark recommendation as rejected; starts back-off window."""
        for key, rec in self._recommendations.items():
            if rec.recommendation_id == recommendation_id and rec.status == "pending":
                rec.status = "rejected"
                rec.rejected_at = datetime.now(timezone.utc)
                return

    def record_irrigation_complete(self, zone_id: str):
        """Record that irrigation completed; starts cool-down window."""
        self._last_irrigated[zone_id] = datetime.now(timezone.utc)
        # Clear approved recommendation for this zone
        key = f"{zone_id}:irrigate"
        if key in self._recommendations:
            del self._recommendations[key]

    def get_pending_recommendations(self) -> list[dict]:
        """Return list of pending recommendation dicts for WebSocket broadcast."""
        result = []
        for key, rec in self._recommendations.items():
            if rec.status == "pending":
                result.append({
                    "recommendation_id": rec.recommendation_id,
                    "zone_id": rec.zone_id,
                    "rec_type": rec.rec_type,
                    "action_description": f"Irrigate {rec.zone_id}",
                    "sensor_reading": "",  # Will be populated on next evaluation
                    "explanation": "Below low threshold",
                })
        return result
