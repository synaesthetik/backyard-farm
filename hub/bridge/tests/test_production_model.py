"""Unit tests for production_model.py — RED phase.

Tests cover age factor curve, daylight factor, expected production calculation,
and BREED_LAY_RATES table completeness.
"""
import pytest
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from production_model import (
    compute_age_factor,
    compute_daylight_factor,
    compute_expected_production,
    BREED_LAY_RATES,
)


class TestComputeAgeFactor:
    def test_ramp_phase_12_weeks(self):
        """12 weeks = ramp phase, factor ~0.5."""
        hatch_date = date.today() - timedelta(weeks=12)
        factor = compute_age_factor(hatch_date)
        assert abs(factor - 0.5) < 0.05

    def test_plateau_40_weeks(self):
        """40 weeks = plateau, factor 1.0."""
        hatch_date = date.today() - timedelta(weeks=40)
        factor = compute_age_factor(hatch_date)
        assert factor == 1.0

    def test_decline_124_weeks(self):
        """124 weeks ≈ 1 year past peak (72 weeks), factor ~0.85 (decline 0.15/year)."""
        hatch_date = date.today() - timedelta(weeks=124)
        factor = compute_age_factor(hatch_date)
        assert abs(factor - 0.85) < 0.05

    def test_minimum_floor_10_years(self):
        """10 years old — should hit floor at 0.2."""
        hatch_date = date.today() - timedelta(weeks=520)  # 10 years
        factor = compute_age_factor(hatch_date)
        assert factor == pytest.approx(0.2, abs=0.05)

    def test_age_factor_never_below_floor(self):
        """Even very old birds never go below 0.2."""
        hatch_date = date.today() - timedelta(weeks=1040)  # 20 years
        factor = compute_age_factor(hatch_date)
        assert factor >= 0.2

    def test_plateau_72_weeks(self):
        """72 weeks = end of plateau, still 1.0."""
        hatch_date = date.today() - timedelta(weeks=72)
        factor = compute_age_factor(hatch_date)
        assert factor == pytest.approx(1.0, abs=0.01)

    def test_custom_today(self):
        """compute_age_factor accepts explicit today parameter."""
        today = date(2025, 1, 1)
        hatch_date = date(2024, 7, 1)  # ~26 weeks prior — plateau
        factor = compute_age_factor(hatch_date, today=today)
        assert factor == pytest.approx(1.0, abs=0.05)


class TestComputeDaylightFactor:
    def test_supplemental_lighting_returns_one(self):
        """Supplemental lighting always returns 1.0."""
        factor = compute_daylight_factor(
            lat=40.0, lon=-75.0,
            today=date(2026, 1, 15),
            supplemental_lighting=True,
        )
        assert factor == 1.0

    def test_summer_northern_hemisphere_high_factor(self):
        """Summer solstice in northern hemisphere — long days → high factor (0.7-1.0)."""
        factor = compute_daylight_factor(
            lat=40.0, lon=-75.0,
            today=date(2026, 6, 21),
            supplemental_lighting=False,
        )
        assert 0.7 <= factor <= 1.0

    def test_unconfigured_location_returns_default(self):
        """lat=0.0, lon=0.0 (not configured) returns 0.85 default."""
        factor = compute_daylight_factor(
            lat=0.0, lon=0.0,
            today=date(2026, 3, 15),
            supplemental_lighting=False,
        )
        assert factor == 0.85

    def test_factor_capped_at_one(self):
        """Factor never exceeds 1.0 even in long-day extremes."""
        factor = compute_daylight_factor(
            lat=60.0, lon=0.0,
            today=date(2026, 6, 21),
            supplemental_lighting=False,
        )
        assert factor <= 1.0

    def test_factor_positive(self):
        """Factor is always positive."""
        factor = compute_daylight_factor(
            lat=40.0, lon=-75.0,
            today=date(2026, 12, 21),
            supplemental_lighting=False,
        )
        assert factor > 0.0


class TestComputeExpectedProduction:
    def test_basic_calculation(self):
        """6 hens x 0.75 lay_rate x 1.0 age x 1.0 daylight = 4.5."""
        result = compute_expected_production(
            flock_size=6, lay_rate=0.75, age_factor=1.0, daylight_factor=1.0
        )
        assert result == pytest.approx(4.5)

    def test_with_age_and_daylight_factors(self):
        """4 hens x 0.8 x 0.9 age x 0.8 daylight = 2.304."""
        result = compute_expected_production(
            flock_size=4, lay_rate=0.8, age_factor=0.9, daylight_factor=0.8
        )
        assert result == pytest.approx(2.304)

    def test_zero_flock_size(self):
        """flock_size=0 returns 0.0."""
        result = compute_expected_production(
            flock_size=0, lay_rate=0.75, age_factor=1.0, daylight_factor=1.0
        )
        assert result == 0.0


class TestBreedLayRates:
    def test_at_least_10_breeds(self):
        """BREED_LAY_RATES contains at least 10 breeds."""
        assert len(BREED_LAY_RATES) >= 10

    def test_custom_breed_maps_to_none(self):
        """'Custom' breed maps to None (user must supply their own lay rate)."""
        assert "Custom" in BREED_LAY_RATES
        assert BREED_LAY_RATES["Custom"] is None

    def test_rhode_island_red_present(self):
        """Rhode Island Red is a common breed and should be present."""
        assert "Rhode Island Red" in BREED_LAY_RATES

    def test_all_rates_valid(self):
        """All non-None rates are between 0 and 1."""
        for breed, rate in BREED_LAY_RATES.items():
            if rate is not None:
                assert 0.0 < rate <= 1.0, f"Breed {breed} has invalid rate {rate}"
