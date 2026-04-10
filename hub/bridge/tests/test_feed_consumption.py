"""Unit tests for feed_consumption.py — RED phase.

Tests cover normal consumption, refill detection, zero consumption,
and edge cases.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from feed_consumption import compute_daily_feed_consumption


class TestComputeDailyFeedConsumption:
    def test_normal_consumption(self):
        """5000 → 4800 = 200g consumed, no refill."""
        consumption, refill_detected = compute_daily_feed_consumption(
            start_weight=5000.0, end_weight=4800.0
        )
        assert consumption == pytest.approx(200.0)
        assert refill_detected is False

    def test_refill_detected(self):
        """3000 → 5000 = end > start, refill detected. Returns (None, True)."""
        consumption, refill_detected = compute_daily_feed_consumption(
            start_weight=3000.0, end_weight=5000.0
        )
        assert consumption is None
        assert refill_detected is True

    def test_zero_consumption(self):
        """5000 → 5000 = 0g consumed, no refill."""
        consumption, refill_detected = compute_daily_feed_consumption(
            start_weight=5000.0, end_weight=5000.0
        )
        assert consumption == pytest.approx(0.0)
        assert refill_detected is False

    def test_large_consumption(self):
        """10000 → 500 = 9500g consumed (full day depletion)."""
        consumption, refill_detected = compute_daily_feed_consumption(
            start_weight=10000.0, end_weight=500.0
        )
        assert consumption == pytest.approx(9500.0)
        assert refill_detected is False

    def test_small_consumption(self):
        """4999 → 4998 = 1g consumed."""
        consumption, refill_detected = compute_daily_feed_consumption(
            start_weight=4999.0, end_weight=4998.0
        )
        assert consumption == pytest.approx(1.0)
        assert refill_detected is False

    def test_return_type_is_tuple(self):
        """Returns a tuple of (float|None, bool)."""
        result = compute_daily_feed_consumption(start_weight=5000.0, end_weight=4800.0)
        assert isinstance(result, tuple)
        assert len(result) == 2
