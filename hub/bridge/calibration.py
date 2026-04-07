"""Calibration offset application at ingestion (ZONE-03).

Calibration offsets are stored per-sensor on the hub. Raw ADC values
from edge nodes have offsets applied before writing to TimescaleDB.
Edge nodes always send raw values — recalibration requires no edge changes.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CalibrationStore:
    """In-memory cache of calibration offsets, loaded from TimescaleDB."""

    def __init__(self):
        # Key: (zone_id, sensor_type) -> offset_value
        self._offsets: dict[tuple[str, str], float] = {}

    async def load_from_db(self, db_pool):
        """Load all calibration offsets from the calibration_offsets table."""
        rows = await db_pool.fetch(
            "SELECT zone_id, sensor_type, offset_value FROM calibration_offsets"
        )
        self._offsets = {
            (row["zone_id"], row["sensor_type"]): row["offset_value"]
            for row in rows
        }
        logger.info("Loaded %d calibration offsets", len(self._offsets))

    def set_offset(self, zone_id: str, sensor_type: str, offset: float):
        """Set calibration offset (for testing or manual override)."""
        self._offsets[(zone_id, sensor_type)] = offset

    def apply_calibration(
        self, zone_id: str, sensor_type: str, raw_value: float
    ) -> tuple[float, bool]:
        """Apply calibration offset to raw value.

        Returns (calibrated_value, calibration_applied).
        If no offset exists, returns (raw_value, False).
        """
        key = (zone_id, sensor_type)
        offset = self._offsets.get(key)

        if offset is not None:
            return (raw_value + offset, True)

        return (raw_value, False)
