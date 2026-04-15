"""Flock REST API endpoints.

Provides:
  GET  /api/flock/config          — current flock configuration
  PUT  /api/flock/config          — upsert flock configuration
  GET  /api/flock/egg-history     — actual vs expected egg counts for charting
  POST /api/flock/refresh-eggs    — trigger immediate egg count estimation

Follows the actuator_router.py pattern: APIRouter, imports get_db_pool from main.
Parameterized queries ($1 placeholders) throughout to prevent SQL injection.
"""
import logging
import sys
import os
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class FlockConfigRequest(BaseModel):
    breed: str = "Rhode Island Red"
    lay_rate_override: Optional[float] = None
    hatch_date: str  # ISO date string "YYYY-MM-DD"
    flock_size: int
    supplemental_lighting: bool = False
    hen_weight_threshold_grams: float = 1500.0
    egg_weight_grams: float = 60.0
    tare_weight_grams: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0


class FlockConfigResponse(BaseModel):
    breed: str
    lay_rate_override: Optional[float]
    hatch_date: str
    flock_size: int
    supplemental_lighting: bool
    hen_weight_threshold_grams: float
    egg_weight_grams: float
    tare_weight_grams: float
    latitude: float
    longitude: float


class EggHistoryPoint(BaseModel):
    date: str
    actual_count: Optional[int]
    expected_count: float


class RefreshEggsResponse(BaseModel):
    estimated_count: int
    hen_present: bool
    raw_weight_grams: float


# ---------------------------------------------------------------------------
# Helpers to resolve bridge module imports (bridge runs in a separate container
# but flock_router is in the api container — we replicate only the pure
# functions needed here to avoid container coupling).
# ---------------------------------------------------------------------------

def _compute_expected(flock_size: int, lay_rate_override: Optional[float], breed: str,
                      hatch_date_obj: date, supplemental_lighting: bool,
                      lat: float, lon: float, target_date: date) -> float:
    """Compute expected daily egg production for a given date.

    This mirrors the bridge's production_model logic inline so the API
    container does not depend on the bridge package at runtime.
    """
    # --- breed lay rate ---
    BREED_LAY_RATES = {
        "Rhode Island Red": 0.75,
        "Leghorn": 0.85,
        "Plymouth Rock (Barred)": 0.70,
        "Sussex": 0.72,
        "Orpington": 0.60,
        "Australorp": 0.78,
        "Marans": 0.55,
        "Wyandotte": 0.65,
        "Ameraucana": 0.62,
        "Silkie": 0.40,
        "Brahma": 0.55,
        "Cochin": 0.50,
        "Custom": None,
    }

    if lay_rate_override is not None:
        lay_rate = lay_rate_override
    else:
        lay_rate = BREED_LAY_RATES.get(breed, 0.75) or 0.75

    # --- age factor (piecewise linear) ---
    age_days = (target_date - hatch_date_obj).days
    age_weeks = age_days / 7.0

    if age_weeks < 0:
        age_factor = 0.0
    elif age_weeks < 24:
        age_factor = age_weeks / 24.0
    elif age_weeks <= 72:
        age_factor = 1.0
    else:
        years_past = (age_weeks - 72.0) / 52.0
        age_factor = max(0.2, 1.0 - 0.15 * years_past)

    # --- daylight factor ---
    if supplemental_lighting:
        daylight_factor = 1.0
    elif lat == 0.0 and lon == 0.0:
        daylight_factor = 0.85
    else:
        try:
            from astral import LocationInfo
            from astral.sun import sun
            from datetime import timedelta as _td

            location = LocationInfo(latitude=lat, longitude=lon)
            s = sun(location.observer, date=target_date)
            sunrise = s["sunrise"]
            sunset = s["sunset"]
            if sunset < sunrise:
                sunset = sunset + _td(days=1)
            daylight_hours = (sunset - sunrise).total_seconds() / 3600.0
            daylight_factor = min(1.0, daylight_hours / 17.0)
        except Exception as exc:
            logger.warning("Daylight factor failed: %s — using 0.85", exc)
            daylight_factor = 0.85

    return flock_size * lay_rate * age_factor * daylight_factor


def _estimate_eggs(weight_grams: float, hen_weight_threshold: float,
                   egg_weight: float, tare_weight: float) -> tuple[int, bool]:
    """Estimate egg count from raw weight. Mirrors egg_estimator.py."""
    net = weight_grams - tare_weight
    hen_present = net >= hen_weight_threshold
    if hen_present:
        egg_only = net - hen_weight_threshold
    else:
        egg_only = net
    egg_only = max(0.0, egg_only)
    if egg_weight <= 0:
        return 0, hen_present
    return max(0, round(egg_only / egg_weight)), hen_present


# ---------------------------------------------------------------------------
# GET /api/flock/config
# ---------------------------------------------------------------------------

@router.get("/api/flock/config", response_model=FlockConfigResponse)
async def get_flock_config():
    """Return current flock configuration from DB, or defaults if none exists."""
    from main import get_db_pool
    pool = get_db_pool()

    row = await pool.fetchrow(
        "SELECT breed, lay_rate_override, hatch_date, flock_size, "
        "supplemental_lighting, hen_weight_threshold_grams, egg_weight_grams, "
        "tare_weight_grams, latitude, longitude "
        "FROM flock_config ORDER BY id DESC LIMIT 1"
    )

    if row:
        return FlockConfigResponse(
            breed=row["breed"],
            lay_rate_override=row["lay_rate_override"],
            hatch_date=row["hatch_date"].isoformat(),
            flock_size=row["flock_size"],
            supplemental_lighting=row["supplemental_lighting"],
            hen_weight_threshold_grams=float(row["hen_weight_threshold_grams"]),
            egg_weight_grams=float(row["egg_weight_grams"]),
            tare_weight_grams=float(row["tare_weight_grams"]),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
        )

    # Return defaults when no row exists
    return FlockConfigResponse(
        breed="Rhode Island Red",
        lay_rate_override=None,
        hatch_date=date.today().isoformat(),
        flock_size=6,
        supplemental_lighting=False,
        hen_weight_threshold_grams=1500.0,
        egg_weight_grams=60.0,
        tare_weight_grams=0.0,
        latitude=0.0,
        longitude=0.0,
    )


# ---------------------------------------------------------------------------
# PUT /api/flock/config
# ---------------------------------------------------------------------------

@router.put("/api/flock/config", response_model=FlockConfigResponse)
async def put_flock_config(body: FlockConfigRequest):
    """Validate and upsert flock configuration."""
    # Validate required numeric constraints
    if body.flock_size < 1:
        raise HTTPException(status_code=422, detail="flock_size must be >= 1")
    if body.egg_weight_grams <= 0:
        raise HTTPException(status_code=422, detail="egg_weight_grams must be > 0")
    if body.hen_weight_threshold_grams <= 0:
        raise HTTPException(status_code=422, detail="hen_weight_threshold_grams must be > 0")

    # Parse hatch_date
    try:
        hatch_date_obj = date.fromisoformat(body.hatch_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="hatch_date must be a valid ISO date (YYYY-MM-DD)")

    from main import get_db_pool
    pool = get_db_pool()

    # Delete existing row(s) and insert fresh (simple upsert for single-row config table)
    await pool.execute("DELETE FROM flock_config")
    await pool.execute(
        "INSERT INTO flock_config "
        "(breed, lay_rate_override, hatch_date, flock_size, supplemental_lighting, "
        "hen_weight_threshold_grams, egg_weight_grams, tare_weight_grams, latitude, longitude) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
        body.breed,
        body.lay_rate_override,
        hatch_date_obj,
        body.flock_size,
        body.supplemental_lighting,
        body.hen_weight_threshold_grams,
        body.egg_weight_grams,
        body.tare_weight_grams,
        body.latitude,
        body.longitude,
    )

    logger.info("Flock config updated: breed=%s, flock_size=%d", body.breed, body.flock_size)

    return FlockConfigResponse(
        breed=body.breed,
        lay_rate_override=body.lay_rate_override,
        hatch_date=hatch_date_obj.isoformat(),
        flock_size=body.flock_size,
        supplemental_lighting=body.supplemental_lighting,
        hen_weight_threshold_grams=body.hen_weight_threshold_grams,
        egg_weight_grams=body.egg_weight_grams,
        tare_weight_grams=body.tare_weight_grams,
        latitude=body.latitude,
        longitude=body.longitude,
    )


# ---------------------------------------------------------------------------
# GET /api/flock/egg-history
# ---------------------------------------------------------------------------

@router.get("/api/flock/egg-history", response_model=list[EggHistoryPoint])
async def egg_history(days: int = Query(30, ge=1, le=90)):
    """Return actual vs expected egg counts for the last N days.

    actual_count: from egg_counts table (None if no record for that day)
    expected_count: computed from flock_config production model
    """
    from main import get_db_pool
    pool = get_db_pool()

    # Load config
    row = await pool.fetchrow(
        "SELECT breed, lay_rate_override, hatch_date, flock_size, "
        "supplemental_lighting, hen_weight_threshold_grams, egg_weight_grams, "
        "tare_weight_grams, latitude, longitude "
        "FROM flock_config ORDER BY id DESC LIMIT 1"
    )

    if row:
        breed = row["breed"]
        lay_rate_override = row["lay_rate_override"]
        hatch_date_obj = row["hatch_date"]
        flock_size = row["flock_size"]
        supplemental_lighting = row["supplemental_lighting"]
        lat = float(row["latitude"])
        lon = float(row["longitude"])
    else:
        # Defaults
        breed = "Rhode Island Red"
        lay_rate_override = None
        hatch_date_obj = date.today()
        flock_size = 6
        supplemental_lighting = False
        lat = 0.0
        lon = 0.0

    # Fetch actual egg counts for the date range (parameterized)
    actual_rows = await pool.fetch(
        "SELECT count_date, estimated_count FROM egg_counts "
        "WHERE count_date >= $1 ORDER BY count_date ASC",
        date.today() - timedelta(days=days - 1),
    )
    actual_by_date = {r["count_date"]: r["estimated_count"] for r in actual_rows}

    # Build result for each day in the range
    result = []
    today = date.today()
    for i in range(days - 1, -1, -1):
        target_date = today - timedelta(days=i)
        expected = _compute_expected(
            flock_size=flock_size,
            lay_rate_override=lay_rate_override,
            breed=breed,
            hatch_date_obj=hatch_date_obj,
            supplemental_lighting=supplemental_lighting,
            lat=lat,
            lon=lon,
            target_date=target_date,
        )
        result.append(EggHistoryPoint(
            date=target_date.isoformat(),
            actual_count=actual_by_date.get(target_date),
            expected_count=round(expected, 2),
        ))

    return result


# ---------------------------------------------------------------------------
# POST /api/flock/refresh-eggs
# ---------------------------------------------------------------------------

@router.post("/api/flock/refresh-eggs", response_model=RefreshEggsResponse)
async def refresh_eggs():
    """Trigger immediate egg count estimation from the latest nesting box reading.

    Queries the most recent sensor_reading for nesting_box_weight,
    estimates egg count, upserts into egg_counts, and returns the result.
    Returns 404 if no recent reading is available.
    """
    from main import get_db_pool
    pool = get_db_pool()

    # Fetch config
    config_row = await pool.fetchrow(
        "SELECT hen_weight_threshold_grams, egg_weight_grams, tare_weight_grams "
        "FROM flock_config ORDER BY id DESC LIMIT 1"
    )

    if config_row:
        hen_threshold = float(config_row["hen_weight_threshold_grams"])
        egg_weight = float(config_row["egg_weight_grams"])
        tare_weight = float(config_row["tare_weight_grams"])
    else:
        # Defaults
        hen_threshold = 1500.0
        egg_weight = 60.0
        tare_weight = 0.0

    # Get latest nesting box weight reading (parameterized zone + sensor_type)
    reading_row = await pool.fetchrow(
        "SELECT value FROM sensor_readings "
        "WHERE zone_id = $1 AND sensor_type = $2 "
        "ORDER BY time DESC LIMIT 1",
        "coop",
        "nesting_box_weight",
    )

    if not reading_row:
        raise HTTPException(status_code=404, detail="No recent nesting box reading available")

    raw_weight = float(reading_row["value"])
    estimated_count, hen_present = _estimate_eggs(
        weight_grams=raw_weight,
        hen_weight_threshold=hen_threshold,
        egg_weight=egg_weight,
        tare_weight=tare_weight,
    )

    # Upsert into egg_counts for today
    today = date.today()
    await pool.execute(
        "INSERT INTO egg_counts (count_date, estimated_count, raw_weight_grams) "
        "VALUES ($1, $2, $3) "
        "ON CONFLICT (count_date) DO UPDATE SET "
        "estimated_count = EXCLUDED.estimated_count, "
        "raw_weight_grams = EXCLUDED.raw_weight_grams",
        today,
        estimated_count,
        raw_weight,
    )

    logger.info(
        "Refresh eggs: weight=%.1fg, estimated=%d, hen_present=%s",
        raw_weight, estimated_count, hen_present,
    )

    return RefreshEggsResponse(
        estimated_count=estimated_count,
        hen_present=hen_present,
        raw_weight_grams=raw_weight,
    )
