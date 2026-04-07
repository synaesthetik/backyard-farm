"""Quality flag logic — range-based per sensor type (D-10, D-11).

Flags are applied at ingestion (stateless range check).
Stuck detection tracks consecutive identical values per sensor (D-12).
"""
import os
from models import QualityFlag

# Configurable ranges via env vars (D-11)
RANGES = {
    "moisture": {
        "bad_min": float(os.getenv("MOISTURE_BAD_MIN", "-0.001")),
        "bad_max": float(os.getenv("MOISTURE_BAD_MAX", "100.001")),
        "suspect_min": float(os.getenv("MOISTURE_SUSPECT_MIN", "2.0")),
        "suspect_max": float(os.getenv("MOISTURE_SUSPECT_MAX", "98.0")),
    },
    "ph": {
        "bad_min": float(os.getenv("PH_BAD_MIN", "0.0")),
        "bad_max": float(os.getenv("PH_BAD_MAX", "14.0")),
        "suspect_min": float(os.getenv("PH_SUSPECT_MIN", "3.0")),
        "suspect_max": float(os.getenv("PH_SUSPECT_MAX", "10.0")),
    },
    "temperature": {
        "bad_min": float(os.getenv("TEMP_BAD_MIN", "-10.0")),
        "bad_max": float(os.getenv("TEMP_BAD_MAX", "80.0")),
        "suspect_min": float(os.getenv("TEMP_SUSPECT_MIN", "0.0")),
        "suspect_max": float(os.getenv("TEMP_SUSPECT_MAX", "60.0")),
    },
}

# Stuck detection threshold (D-12)
STUCK_THRESHOLD = int(os.getenv("STUCK_READING_THRESHOLD", "30"))


def apply_quality_flag(sensor_type: str, value: float) -> QualityFlag:
    """Apply quality flag based on range check.

    Returns GOOD, SUSPECT, or BAD.
    Unknown sensor types default to GOOD (no range defined).
    """
    ranges = RANGES.get(sensor_type)
    if ranges is None:
        return QualityFlag.GOOD

    if value < ranges["bad_min"] or value > ranges["bad_max"]:
        return QualityFlag.BAD

    if value < ranges["suspect_min"] or value > ranges["suspect_max"]:
        return QualityFlag.SUSPECT

    return QualityFlag.GOOD


class StuckDetector:
    """Tracks consecutive identical readings per sensor (D-12).

    A sensor is STUCK when it returns the same value for STUCK_THRESHOLD
    consecutive readings. STUCK is a display state — it does NOT change
    the quality flag. A GOOD + STUCK reading is still GOOD.
    """

    def __init__(self, threshold: int = STUCK_THRESHOLD):
        self.threshold = threshold
        # Key: (zone_id, sensor_type) -> (last_value, consecutive_count)
        self._counters: dict[tuple[str, str], tuple[float, int]] = {}

    def check(self, zone_id: str, sensor_type: str, value: float) -> bool:
        """Returns True if sensor is stuck (>=threshold consecutive identical values)."""
        key = (zone_id, sensor_type)
        prev = self._counters.get(key)

        if prev is not None and prev[0] == value:
            count = prev[1] + 1
        else:
            count = 1

        self._counters[key] = (value, count)
        return count >= self.threshold
