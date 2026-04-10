"""Unit tests for egg_estimator.py — RED phase.

Tests cover egg count estimation from nesting box weight,
hen presence detection, tare subtraction, and edge cases.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from egg_estimator import estimate_egg_count
from flock_config import FlockConfig
from datetime import date


def make_config(
    egg_weight_grams: float = 60.0,
    hen_weight_threshold_grams: float = 1500.0,
    tare_weight_grams: float = 0.0,
) -> FlockConfig:
    return FlockConfig(
        breed="Rhode Island Red",
        flock_size=6,
        hatch_date=date.today(),
        supplemental_lighting=False,
        hen_weight_threshold_grams=hen_weight_threshold_grams,
        egg_weight_grams=egg_weight_grams,
        tare_weight_grams=tare_weight_grams,
        latitude=0.0,
        longitude=0.0,
    )


class TestEstimateEggCount:
    def test_five_eggs_no_hen(self):
        """300g / 60g = 5 eggs, no hen present."""
        config = make_config(egg_weight_grams=60.0, hen_weight_threshold_grams=1500.0)
        count, hen_present = estimate_egg_count(300.0, config)
        assert count == 5
        assert hen_present is False

    def test_five_eggs_with_hen(self):
        """1800g - 1500g hen = 300g / 60g = 5 eggs, hen present."""
        config = make_config(egg_weight_grams=60.0, hen_weight_threshold_grams=1500.0)
        count, hen_present = estimate_egg_count(1800.0, config)
        assert count == 5
        assert hen_present is True

    def test_empty_box(self):
        """0g returns (0, False) — empty box."""
        config = make_config()
        count, hen_present = estimate_egg_count(0.0, config)
        assert count == 0
        assert hen_present is False

    def test_hen_only_no_eggs(self):
        """Exactly hen weight threshold — hen present, 0 effective egg weight."""
        config = make_config(egg_weight_grams=60.0, hen_weight_threshold_grams=1500.0)
        count, hen_present = estimate_egg_count(1500.0, config)
        assert count == 0
        assert hen_present is True

    def test_below_one_egg_rounds_to_zero(self):
        """25g < 60g egg weight — below one egg rounds to 0."""
        config = make_config(egg_weight_grams=60.0)
        count, hen_present = estimate_egg_count(25.0, config)
        assert count == 0
        assert hen_present is False

    def test_tare_weight_subtracted(self):
        """400g with 100g tare → (400-100) / 60 = 5 eggs."""
        config = make_config(egg_weight_grams=60.0, tare_weight_grams=100.0, hen_weight_threshold_grams=1500.0)
        count, hen_present = estimate_egg_count(400.0, config)
        assert count == 5
        assert hen_present is False

    def test_negative_weight_returns_zero(self):
        """Weight below tare weight clamps to 0 eggs."""
        config = make_config(tare_weight_grams=50.0)
        count, hen_present = estimate_egg_count(30.0, config)
        assert count == 0
        assert hen_present is False

    def test_rounding_half_up(self):
        """90g / 60g = 1.5 eggs — rounds to 2."""
        config = make_config(egg_weight_grams=60.0)
        count, hen_present = estimate_egg_count(90.0, config)
        assert count == 2
        assert hen_present is False

    def test_hen_present_only_weight_exactly_threshold(self):
        """Weight exactly equals hen threshold — hen present, 0 eggs."""
        config = make_config(egg_weight_grams=60.0, hen_weight_threshold_grams=2000.0)
        count, hen_present = estimate_egg_count(2000.0, config)
        assert count == 0
        assert hen_present is True

    def test_no_negative_count(self):
        """Ensures egg count is never negative."""
        config = make_config(egg_weight_grams=60.0)
        count, hen_present = estimate_egg_count(-100.0, config)
        assert count == 0
