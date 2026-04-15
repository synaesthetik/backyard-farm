"""Tests for feature_aggregator.py (Task 04-01-T1).

Uses unittest.mock.AsyncMock to mock db_pool — no running database required.
"""
import math
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import AsyncMock, MagicMock, patch, call
from inference.feature_aggregator import FeatureAggregator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_db_pool():
    """Return a mock asyncpg pool with configurable fetch/fetchrow responses."""
    pool = MagicMock()
    pool.fetch = AsyncMock()
    pool.fetchrow = AsyncMock()
    pool.execute = AsyncMock()
    return pool


def make_row(sensor_type, mean_val, min_val, max_val, std_val, reading_count):
    """Return a dict that mimics an asyncpg Record for a sensor aggregate row."""
    return {
        "sensor_type": sensor_type,
        "mean_val": mean_val,
        "min_val": min_val,
        "max_val": max_val,
        "std_val": std_val,
        "reading_count": reading_count,
    }


# ---------------------------------------------------------------------------
# Test 1: aggregate_zone_features() with all GOOD readings returns correct dict
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aggregate_zone_features_returns_correct_keys():
    """All GOOD readings for a single sensor type returns a stats dict."""
    pool = make_db_pool()
    pool.fetch.return_value = [
        make_row("moisture", 42.0, 38.0, 46.0, 2.1, 12),
    ]

    agg = FeatureAggregator(pool)
    result = await agg.aggregate_zone_features("zone-01", ["moisture"], window_hours=24)

    assert result is not None
    assert "moisture" in result
    stats = result["moisture"]
    assert "mean_val" in stats
    assert "min_val" in stats
    assert "max_val" in stats
    assert "std_val" in stats
    assert "reading_count" in stats
    assert stats["mean_val"] == pytest.approx(42.0)
    assert stats["reading_count"] == 12


# ---------------------------------------------------------------------------
# Test 2: aggregate_zone_features() excludes non-GOOD rows at SQL level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aggregate_zone_features_good_flag_in_sql():
    """The SQL query passed to db_pool.fetch must contain quality = 'GOOD' in the WHERE clause."""
    pool = make_db_pool()
    pool.fetch.return_value = [
        make_row("moisture", 40.0, 35.0, 45.0, 2.5, 8),
        make_row("ph", 6.5, 6.3, 6.7, 0.1, 8),
    ]

    agg = FeatureAggregator(pool)
    # Pool returns only GOOD rows — the filtering is in the SQL, not Python
    await agg.aggregate_zone_features("zone-01", ["moisture", "ph"], window_hours=24)

    # Verify that the SQL string passed to fetch contains the mandatory GOOD filter
    assert pool.fetch.called, "db_pool.fetch should have been called"
    call_args = pool.fetch.call_args
    sql_arg = call_args[0][0]  # first positional argument is the SQL string
    assert "quality = 'GOOD'" in sql_arg, (
        f"SQL must contain \"quality = 'GOOD'\" filter but got:\n{sql_arg}"
    )


# ---------------------------------------------------------------------------
# Test 3: aggregate_zone_features() returns None when fewer than MIN_READINGS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aggregate_zone_features_none_when_insufficient_readings():
    """Returns None when total GOOD reading_count across all sensors < MIN_READINGS (10)."""
    pool = make_db_pool()
    # Only 3 GOOD readings for moisture — below MIN_READINGS=10
    pool.fetch.return_value = [
        make_row("moisture", 41.0, 39.0, 43.0, 1.0, 3),
    ]

    agg = FeatureAggregator(pool)
    with patch.dict(os.environ, {"MIN_READINGS": "10"}):
        result = await agg.aggregate_zone_features("zone-01", ["moisture"], window_hours=24)

    assert result is None, "Should return None when insufficient GOOD readings"


# ---------------------------------------------------------------------------
# Test 4: build_feature_vector() returns fixed-length list with NaN for missing sensors
# ---------------------------------------------------------------------------

def test_build_feature_vector_fixed_length_with_nan_sentinel():
    """build_feature_vector returns flat list of fixed length; missing sensors get NaN * 4."""
    pool = make_db_pool()
    agg = FeatureAggregator(pool)

    sensor_types = ["moisture", "ph", "temperature"]
    aggregated = {
        "moisture": {"mean_val": 42.0, "min_val": 38.0, "max_val": 46.0, "std_val": 2.1},
        # ph and temperature are missing
    }

    vector = agg.build_feature_vector(aggregated, sensor_types)

    assert isinstance(vector, list)
    assert len(vector) == len(sensor_types) * 4, (
        f"Expected {len(sensor_types) * 4} elements, got {len(vector)}"
    )
    # moisture values present
    assert vector[0] == pytest.approx(42.0)
    assert vector[1] == pytest.approx(38.0)
    assert vector[2] == pytest.approx(46.0)
    assert vector[3] == pytest.approx(2.1)
    # ph and temperature are NaN
    for i in range(4, 12):
        assert math.isnan(vector[i]), f"Element {i} should be NaN but got {vector[i]}"


# ---------------------------------------------------------------------------
# Test 5: check_data_maturity() returns gate_passed=True when ratio >= 0.8 AND span >= 28 days
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_data_maturity_gate_passes_when_conditions_met():
    """gate_passed=True when good_ratio >= 0.8 AND data_span_days >= 28."""
    pool = make_db_pool()
    # good_ratio = 0.85, data_span approximately 30 days
    from datetime import timedelta
    pool.fetchrow.return_value = {
        "good_ratio": 0.85,
        "earliest_reading": None,
        "data_span": timedelta(days=30),
    }

    agg = FeatureAggregator(pool)
    result = await agg.check_data_maturity("zone-01")

    assert result["gate_passed"] is True
    assert result["good_ratio"] == pytest.approx(0.85)
    assert result["data_span_days"] == pytest.approx(30.0)
    assert result["zone_id"] == "zone-01"


# ---------------------------------------------------------------------------
# Test 6: check_data_maturity() returns gate_passed=False when good_ratio < 0.8
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_data_maturity_fails_when_ratio_too_low():
    """gate_passed=False when good_ratio < 0.8, even if data_span >= 28 days."""
    pool = make_db_pool()
    from datetime import timedelta
    pool.fetchrow.return_value = {
        "good_ratio": 0.70,
        "earliest_reading": None,
        "data_span": timedelta(days=35),
    }

    agg = FeatureAggregator(pool)
    result = await agg.check_data_maturity("zone-01")

    assert result["gate_passed"] is False


# ---------------------------------------------------------------------------
# Test 7: check_data_maturity() returns gate_passed=False when span < 4 weeks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_data_maturity_fails_when_data_span_insufficient():
    """gate_passed=False when data_span < 28 days, even if good_ratio >= 0.8."""
    pool = make_db_pool()
    from datetime import timedelta
    pool.fetchrow.return_value = {
        "good_ratio": 0.90,
        "earliest_reading": None,
        "data_span": timedelta(days=20),
    }

    agg = FeatureAggregator(pool)
    result = await agg.check_data_maturity("zone-01")

    assert result["gate_passed"] is False


# ---------------------------------------------------------------------------
# Test 8: build_feature_vector() converts aggregated stats into a flat float list
# ---------------------------------------------------------------------------

def test_build_feature_vector_all_sensors_present():
    """build_feature_vector with all sensors present returns a correct flat list."""
    pool = make_db_pool()
    agg = FeatureAggregator(pool)

    sensor_types = ["moisture", "ph"]
    aggregated = {
        "moisture": {"mean_val": 42.0, "min_val": 38.0, "max_val": 46.0, "std_val": 2.1},
        "ph": {"mean_val": 6.5, "min_val": 6.3, "max_val": 6.7, "std_val": 0.1},
    }

    vector = agg.build_feature_vector(aggregated, sensor_types)

    assert len(vector) == 8
    assert vector[0] == pytest.approx(42.0)  # moisture mean
    assert vector[1] == pytest.approx(38.0)  # moisture min
    assert vector[2] == pytest.approx(46.0)  # moisture max
    assert vector[3] == pytest.approx(2.1)   # moisture std
    assert vector[4] == pytest.approx(6.5)   # ph mean
    assert vector[5] == pytest.approx(6.3)   # ph min
    assert vector[6] == pytest.approx(6.7)   # ph max
    assert vector[7] == pytest.approx(0.1)   # ph std
