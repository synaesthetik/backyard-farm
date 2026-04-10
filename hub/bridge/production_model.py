"""Expected egg production model.

Computes:
  - Age factor (piecewise linear curve per research Pattern 8)
  - Daylight factor (via astral or fallback per research Pattern 10)
  - Expected production: flock_size × breed_lay_rate × age_factor × daylight_factor

Per D-06, D-10, D-11, research Patterns 8-10.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Breed lay rates (eggs per hen per day at peak)
# Common breeds sourced from poultry husbandry references.
# "Custom" maps to None — user must supply their own lay_rate_override.
BREED_LAY_RATES: dict[str, float | None] = {
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

# Age factor curve parameters (per D-11 + research Pattern 8)
_RAMP_START_WEEKS = 0      # Weeks at hatch
_RAMP_END_WEEKS = 24       # Peak laying begins ~24 weeks
_PLATEAU_END_WEEKS = 72    # Peak plateau ends at ~72 weeks (~18 months)
_DECLINE_RATE = 0.15       # Factor drop per year after plateau
_AGE_FACTOR_FLOOR = 0.2    # Minimum age factor


def compute_age_factor(hatch_date: date, today: date | None = None) -> float:
    """Compute piecewise linear age factor from hatch date.

    Curve (per research Pattern 8, D-11):
      - 0 to 24 weeks: linear ramp 0.0 → 1.0
      - 24 to 72 weeks: plateau at 1.0
      - 72+ weeks: linear decline at 0.15 per year, floor at 0.2

    Args:
        hatch_date: Date the flock hatched.
        today: Override today's date (for testing). Defaults to date.today().

    Returns:
        Age factor in range [0.2, 1.0].
    """
    if today is None:
        today = date.today()

    age_days = (today - hatch_date).days
    age_weeks = age_days / 7.0

    if age_weeks < _RAMP_START_WEEKS:
        return 0.0

    if age_weeks < _RAMP_END_WEEKS:
        # Linear ramp from 0.0 to 1.0 over 0-24 weeks
        return age_weeks / _RAMP_END_WEEKS

    if age_weeks <= _PLATEAU_END_WEEKS:
        # Plateau
        return 1.0

    # Decline phase: 0.15 per year past plateau end
    years_past_plateau = (age_weeks - _PLATEAU_END_WEEKS) / 52.0
    factor = 1.0 - (_DECLINE_RATE * years_past_plateau)
    return max(_AGE_FACTOR_FLOOR, factor)


def compute_daylight_factor(
    lat: float,
    lon: float,
    today: date,
    supplemental_lighting: bool,
) -> float:
    """Compute daylight factor based on sunrise/sunset times.

    If supplemental_lighting is True, returns 1.0 (artificially extended daylight).
    If lat/lon are 0.0/0.0 (not configured), returns 0.85 default.
    Otherwise uses astral to compute daylight hours, scaled to 17h maximum.

    Args:
        lat: Latitude of the coop location.
        lon: Longitude of the coop location.
        today: Date for daylight calculation.
        supplemental_lighting: Whether supplemental lighting extends daylight.

    Returns:
        Daylight factor in range (0.0, 1.0].
    """
    if supplemental_lighting:
        return 1.0

    # Unconfigured location fallback (per research Pattern 10, open question 1)
    if lat == 0.0 and lon == 0.0:
        return 0.85

    try:
        from astral import LocationInfo
        from astral.sun import sun

        location = LocationInfo(latitude=lat, longitude=lon)
        s = sun(location.observer, date=today)
        sunrise = s["sunrise"]
        sunset = s["sunset"]
        # astral returns UTC times; sunset may be numerically before sunrise when
        # the local solar day crosses UTC midnight (e.g. western longitudes in summer).
        # Correct by adding one day to sunset in that case.
        if sunset < sunrise:
            sunset = sunset + timedelta(days=1)
        daylight_seconds = (sunset - sunrise).total_seconds()
        daylight_hours = daylight_seconds / 3600.0
        # Scale: 17 hours = optimal full factor
        factor = daylight_hours / 17.0
        return min(1.0, factor)
    except Exception as e:
        logger.warning("Failed to compute daylight factor via astral: %s — using default 0.85", e)
        return 0.85


def compute_expected_production(
    flock_size: int,
    lay_rate: float,
    age_factor: float,
    daylight_factor: float,
) -> float:
    """Compute expected daily egg production.

    Formula: flock_size × lay_rate × age_factor × daylight_factor

    Args:
        flock_size: Number of laying hens.
        lay_rate: Breed lay rate (eggs per hen per day at peak).
        age_factor: Age factor from compute_age_factor().
        daylight_factor: Daylight factor from compute_daylight_factor().

    Returns:
        Expected number of eggs per day (float).
    """
    return flock_size * lay_rate * age_factor * daylight_factor
