"""Calibration offset application at ingestion (ZONE-03).

Calibration offsets are stored per-sensor on the hub. Raw ADC values
from edge nodes have offsets applied before writing to TimescaleDB.
Edge nodes always send raw values — recalibration requires no edge changes.

Phase 5 extensions (ZONE-07, D-03, D-04):
  - is_overdue(): returns True when last_calibration_date is None or older than 2 weeks
  - record_calibration(): UPSERT calibration record, sets last_calibration_date to NOW()
  - get_all_calibrations(): returns all calibration entries with computed days_since_calibration
  - update_calibration_fields(): field-level update for offset, dry/wet values, temp coefficient
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

TWO_WEEKS = timedelta(weeks=2)


class CalibrationStore:
    """In-memory cache of calibration offsets, loaded from TimescaleDB."""

    def __init__(self):
        # Key: (zone_id, sensor_type) -> offset_value
        self._offsets: dict[tuple[str, str], float] = {}
        # Phase 5: extended fields
        self._calibration_dates: dict[tuple[str, str], Optional[datetime]] = {}
        self._dry_values: dict[tuple[str, str], Optional[float]] = {}
        self._wet_values: dict[tuple[str, str], Optional[float]] = {}
        self._temp_coefficients: dict[tuple[str, str], float] = {}

    async def load_from_db(self, db_pool):
        """Load all calibration offsets from the calibration_offsets table."""
        rows = await db_pool.fetch(
            "SELECT zone_id, sensor_type, offset_value, dry_value, wet_value, temp_coefficient, last_calibration_date FROM calibration_offsets"
        )
        self._offsets = {}
        self._calibration_dates = {}
        self._dry_values = {}
        self._wet_values = {}
        self._temp_coefficients = {}
        for row in rows:
            key = (row["zone_id"], row["sensor_type"])
            self._offsets[key] = row["offset_value"]
            # Defensively ensure tzinfo is set (Pitfall 6 — always aware datetimes)
            cal_date = row["last_calibration_date"]
            if cal_date is not None and cal_date.tzinfo is None:
                cal_date = cal_date.replace(tzinfo=timezone.utc)
            self._calibration_dates[key] = cal_date
            self._dry_values[key] = row["dry_value"]
            self._wet_values[key] = row["wet_value"]
            self._temp_coefficients[key] = row["temp_coefficient"] if row["temp_coefficient"] is not None else 0.0
        logger.info("Loaded %d calibration offsets", len(self._offsets))

    def set_offset(self, zone_id: str, sensor_type: str, offset: float):
        """Set calibration offset (for testing or manual override)."""
        key = (zone_id, sensor_type)
        self._offsets[key] = offset
        # Ensure other dicts have an entry for this key (for get_all_calibrations)
        self._calibration_dates.setdefault(key, None)
        self._dry_values.setdefault(key, None)
        self._wet_values.setdefault(key, None)
        self._temp_coefficients.setdefault(key, 0.0)

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

    def is_overdue(self, zone_id: str, sensor_type: str) -> bool:
        """Return True if calibration is overdue (never calibrated or >2 weeks ago).

        Uses datetime.now(timezone.utc) for comparison to ensure aware datetimes
        (Pitfall 6 — never use datetime.utcnow()).
        Overdue is strictly > TWO_WEEKS, so exactly 14 days is NOT overdue.
        """
        key = (zone_id, sensor_type)
        last_date = self._calibration_dates.get(key)
        if last_date is None:
            return True
        # Defensively add tzinfo if somehow missing
        if last_date.tzinfo is None:
            last_date = last_date.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_date > TWO_WEEKS

    async def record_calibration(
        self,
        zone_id: str,
        sensor_type: str,
        offset: float,
        db_pool,
        dry_value: Optional[float] = None,
        wet_value: Optional[float] = None,
        temp_coefficient: float = 0.0,
    ):
        """Record a calibration event: UPSERT to DB with last_calibration_date = NOW().

        Updates in-memory caches after successful DB write.
        """
        now = datetime.now(timezone.utc)
        await db_pool.execute(
            """
            INSERT INTO calibration_offsets
              (zone_id, sensor_type, offset_value, dry_value, wet_value, temp_coefficient, updated_at, last_calibration_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
            ON CONFLICT (zone_id, sensor_type) DO UPDATE
              SET offset_value = EXCLUDED.offset_value,
                  dry_value = EXCLUDED.dry_value,
                  wet_value = EXCLUDED.wet_value,
                  temp_coefficient = EXCLUDED.temp_coefficient,
                  updated_at = EXCLUDED.updated_at,
                  last_calibration_date = EXCLUDED.last_calibration_date
            """,
            zone_id, sensor_type, offset, dry_value, wet_value, temp_coefficient, now,
        )
        key = (zone_id, sensor_type)
        self._offsets[key] = offset
        self._calibration_dates[key] = now
        self._dry_values[key] = dry_value
        self._wet_values[key] = wet_value
        self._temp_coefficients[key] = temp_coefficient
        logger.info("Recorded calibration for %s/%s: offset=%.4f", zone_id, sensor_type, offset)

    async def update_calibration_fields(
        self,
        zone_id: str,
        sensor_type: str,
        db_pool,
        **fields,
    ):
        """Update specific calibration fields (offset_value, dry_value, wet_value, temp_coefficient).

        Does NOT update last_calibration_date — use record_calibration() for full calibration events.
        """
        allowed = {"offset_value", "dry_value", "wet_value", "temp_coefficient"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return

        set_clauses = ", ".join(f"{col} = ${i+3}" for i, col in enumerate(updates))
        values = list(updates.values())
        await db_pool.execute(
            f"""
            UPDATE calibration_offsets
            SET {set_clauses}, updated_at = NOW()
            WHERE zone_id = $1 AND sensor_type = $2
            """,
            zone_id, sensor_type, *values,
        )
        key = (zone_id, sensor_type)
        if "offset_value" in updates:
            self._offsets[key] = updates["offset_value"]
        if "dry_value" in updates:
            self._dry_values[key] = updates["dry_value"]
        if "wet_value" in updates:
            self._wet_values[key] = updates["wet_value"]
        if "temp_coefficient" in updates:
            self._temp_coefficients[key] = updates["temp_coefficient"]
        logger.info("Updated calibration fields for %s/%s: %s", zone_id, sensor_type, list(updates.keys()))

    def get_all_calibrations(self) -> list[dict]:
        """Return all calibration entries with all fields including computed days_since_calibration."""
        now = datetime.now(timezone.utc)
        result = []
        for key in self._offsets:
            zone_id, sensor_type = key
            last_date = self._calibration_dates.get(key)
            if last_date is not None and last_date.tzinfo is None:
                last_date = last_date.replace(tzinfo=timezone.utc)
            days_since = (now - last_date).total_seconds() / 86400.0 if last_date is not None else None
            result.append({
                "zone_id": zone_id,
                "sensor_type": sensor_type,
                "offset_value": self._offsets[key],
                "dry_value": self._dry_values.get(key),
                "wet_value": self._wet_values.get(key),
                "temp_coefficient": self._temp_coefficients.get(key, 0.0),
                "last_calibration_date": last_date.isoformat() if last_date is not None else None,
                "days_since_calibration": days_since,
            })
        return result
