"""Sensor history endpoint for time-series charts (ZONE-05, D-32).

GET /api/zones/{zone_id}/history?sensor_type={type}&days=7
Returns time-bucketed data from TimescaleDB.
30-minute buckets for 7-day range, 2-hour buckets for 30-day range.
"""
import logging
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter()

HISTORY_QUERY = """
    SELECT
        time_bucket($1::interval, time) AS bucket,
        AVG(value) AS avg_value
    FROM sensor_readings
    WHERE zone_id = $2
      AND sensor_type = $3
      AND time >= NOW() - $4::interval
      AND quality != 'BAD'
    GROUP BY bucket
    ORDER BY bucket ASC
"""


@router.get("/api/zones/{zone_id}/history")
async def zone_history(
    zone_id: str,
    sensor_type: str = Query(..., description="moisture, ph, or temperature"),
    days: int = Query(7, ge=1, le=30, description="7 or 30"),
):
    """Return time-bucketed sensor history for charts."""
    from main import get_db_pool
    pool = get_db_pool()

    bucket_interval = "30 minutes" if days <= 7 else "2 hours"
    range_interval = f"{days} days"

    rows = await pool.fetch(
        HISTORY_QUERY, bucket_interval, zone_id, sensor_type, range_interval
    )

    return [
        {"ts": row["bucket"].isoformat(), "value": float(row["avg_value"]) if row["avg_value"] else None}
        for row in rows
    ]
