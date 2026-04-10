"""Sensor-feedback irrigation loop (IRRIG-05, D-19).

Once an irrigation recommendation is approved, the hub:
1. Commands valve open via MQTT
2. Monitors VWC readings for the irrigating zone
3. Closes valve when target VWC is reached OR max duration exceeded
4. Records irrigation completion for cool-down tracking

This runs as a background task in the bridge's asyncio loop.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MAX_DURATION_MINUTES = int(os.getenv("IRRIGATION_MAX_DURATION_MINUTES", "30"))


class IrrigationLoop:
    def __init__(self):
        self._active_zone: str | None = None
        self._target_vwc: float = 0.0
        self._started_at: datetime | None = None
        self._task: asyncio.Task | None = None

    @property
    def active_zone(self) -> str | None:
        return self._active_zone

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    def start(self, zone_id: str, target_vwc: float):
        """Start monitoring for a zone. Valve open command already sent."""
        self._active_zone = zone_id
        self._target_vwc = target_vwc
        self._started_at = datetime.now(timezone.utc)
        logger.info("Irrigation loop started for %s, target VWC: %.1f%%", zone_id, target_vwc)

    def check_reading(self, zone_id: str, sensor_type: str, value: float) -> str | None:
        """Check if an incoming sensor reading should end the irrigation.

        Returns:
            "target_reached" if VWC >= target
            "max_duration" if max duration exceeded
            None if irrigation should continue
        """
        if self._active_zone != zone_id or sensor_type != "moisture":
            return None

        if value >= self._target_vwc:
            return "target_reached"

        if self._started_at:
            elapsed_min = (datetime.now(timezone.utc) - self._started_at).total_seconds() / 60
            if elapsed_min >= MAX_DURATION_MINUTES:
                return "max_duration"

        return None

    def stop(self):
        """Stop the irrigation loop."""
        zone = self._active_zone
        self._active_zone = None
        self._target_vwc = 0.0
        self._started_at = None
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        logger.info("Irrigation loop stopped for %s", zone)
        return zone
