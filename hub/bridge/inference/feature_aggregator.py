"""Feature aggregation for ONNX inference (AI-06, D-10).

All queries enforce quality = 'GOOD' at the SQL level — this filter is
structural and non-optional per decision D-10. It is never passed as a
parameter and cannot be bypassed by callers.

Exports: FeatureAggregator
"""
import os
from datetime import timedelta
from typing import Optional

import asyncpg


# Sensor types used in zone-level feature vectors
SENSOR_TYPES: list[str] = ["moisture", "ph", "temperature"]

# Sensor types used in flock/coop feature vectors
FLOCK_SENSOR_TYPES: list[str] = ["feed_weight", "nesting_box_weight", "water_level"]

# SQL: aggregate GOOD-flagged sensor readings within a time window.
# quality = 'GOOD' is in the WHERE clause — structural, non-parameterized (AI-06).
FEATURE_QUERY = """
SELECT sensor_type,
       AVG(value)    AS mean_val,
       MIN(value)    AS min_val,
       MAX(value)    AS max_val,
       STDDEV(value) AS std_val,
       COUNT(*)      AS reading_count
FROM sensor_readings
WHERE zone_id = $1
  AND quality = 'GOOD'
  AND time > NOW() - ($2 || ' hours')::interval
GROUP BY sensor_type
"""

# SQL: compute data maturity metrics for the last 4 weeks.
MATURITY_GATE_QUERY = """
SELECT COUNT(*) FILTER (WHERE quality = 'GOOD')::float / NULLIF(COUNT(*), 0) AS good_ratio,
       MIN(time) AS earliest_reading,
       NOW() - MIN(time) AS data_span
FROM sensor_readings
WHERE zone_id = $1
  AND time > NOW() - INTERVAL '4 weeks'
"""


class FeatureAggregator:
    """Queries TimescaleDB for sensor aggregates with mandatory GOOD-flag filtering.

    Args:
        db_pool: An asyncpg connection pool.
    """

    MIN_READINGS: int = int(os.getenv("MIN_READINGS", "10"))

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool

    async def aggregate_zone_features(
        self,
        zone_id: str,
        sensor_types: list[str],
        window_hours: int = 24,
    ) -> Optional[dict[str, dict[str, float]]]:
        """Return per-sensor aggregate statistics for GOOD-flagged readings only.

        Args:
            zone_id: The zone identifier to query.
            sensor_types: List of sensor_type strings to include.
            window_hours: Look-back window in hours (default 24).

        Returns:
            A dict mapping sensor_type -> {mean_val, min_val, max_val, std_val, reading_count},
            or None if total GOOD reading count is below MIN_READINGS.
        """
        rows = await self._pool.fetch(FEATURE_QUERY, zone_id, str(window_hours))

        total_readings = sum(int(row["reading_count"]) for row in rows)
        if total_readings < self.MIN_READINGS:
            return None

        result: dict[str, dict[str, float]] = {}
        for row in rows:
            st = row["sensor_type"]
            if st in sensor_types:
                result[st] = {
                    "mean_val": float(row["mean_val"]) if row["mean_val"] is not None else float("nan"),
                    "min_val": float(row["min_val"]) if row["min_val"] is not None else float("nan"),
                    "max_val": float(row["max_val"]) if row["max_val"] is not None else float("nan"),
                    "std_val": float(row["std_val"]) if row["std_val"] is not None else float("nan"),
                    "reading_count": int(row["reading_count"]),
                }
        return result

    def build_feature_vector(
        self,
        aggregated: dict[str, dict[str, float]],
        sensor_types: list[str],
    ) -> list[float]:
        """Convert aggregated sensor stats into a fixed-length flat float list.

        For each sensor_type in sensor_types, appends [mean, min, max, std].
        Missing sensor types are represented by four NaN sentinels, ensuring
        the ONNX model always receives an input of consistent shape.

        Args:
            aggregated: Output from aggregate_zone_features().
            sensor_types: Ordered list of sensor types that define the vector shape.

        Returns:
            A flat list[float] of length len(sensor_types) * 4.
        """
        vector: list[float] = []
        for st in sensor_types:
            if st in aggregated:
                stats = aggregated[st]
                vector.extend([
                    float(stats.get("mean_val", float("nan"))),
                    float(stats.get("min_val", float("nan"))),
                    float(stats.get("max_val", float("nan"))),
                    float(stats.get("std_val", float("nan"))),
                ])
            else:
                vector.extend([float("nan")] * 4)
        return vector

    async def check_data_maturity(self, zone_id: str) -> dict:
        """Evaluate whether a zone has sufficient high-quality data for ONNX activation.

        Runs the maturity gate query and returns a result dict including
        gate_passed, which is True only when:
          - good_ratio >= 0.8  (at least 80% of readings are GOOD-flagged)
          - data_span_days >= 28  (at least 4 weeks of data history)

        Args:
            zone_id: The zone identifier to evaluate.

        Returns:
            dict with keys: zone_id, good_ratio, data_span_days, gate_passed.
        """
        row = await self._pool.fetchrow(MATURITY_GATE_QUERY, zone_id)

        good_ratio: float = 0.0
        data_span_days: float = 0.0

        if row is not None:
            if row["good_ratio"] is not None:
                good_ratio = float(row["good_ratio"])
            span = row.get("data_span")
            if span is not None:
                if isinstance(span, timedelta):
                    data_span_days = span.total_seconds() / 86400.0
                else:
                    # asyncpg may return a timedelta-compatible object
                    data_span_days = float(span)

        gate_passed = good_ratio >= 0.8 and data_span_days >= 28.0

        return {
            "zone_id": zone_id,
            "good_ratio": good_ratio,
            "data_span_days": data_span_days,
            "gate_passed": gate_passed,
        }
