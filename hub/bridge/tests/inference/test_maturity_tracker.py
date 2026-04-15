"""Tests for maturity_tracker.py (Task 04-01-T2).

Uses unittest.mock.AsyncMock to mock db_pool — no running database required.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import AsyncMock, MagicMock, call
from inference.maturity_tracker import MaturityTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_db_pool():
    pool = MagicMock()
    pool.fetch = AsyncMock()
    pool.fetchrow = AsyncMock()
    pool.execute = AsyncMock()
    return pool


def make_tracker(pool=None):
    if pool is None:
        pool = make_db_pool()
    return MaturityTracker(pool)


# ---------------------------------------------------------------------------
# Test 1: record_recommendation() increments recommendation_count
# ---------------------------------------------------------------------------

def test_record_recommendation_increments_count():
    """record_recommendation increments recommendation_count for the given domain."""
    tracker = make_tracker()

    assert tracker.get_maturity_state("irrigation")["recommendation_count"] == 0
    tracker.record_recommendation("irrigation", "rec-001")
    assert tracker.get_maturity_state("irrigation")["recommendation_count"] == 1
    tracker.record_recommendation("irrigation", "rec-002")
    assert tracker.get_maturity_state("irrigation")["recommendation_count"] == 2


# ---------------------------------------------------------------------------
# Test 2: record_approval() increments approved_count
# ---------------------------------------------------------------------------

def test_record_approval_increments_approved_count():
    """record_approval increments approved_count for the given domain."""
    tracker = make_tracker()
    tracker.record_recommendation("zone_health", "rec-001")
    tracker.record_approval("zone_health")
    state = tracker.get_maturity_state("zone_health")
    assert state["approved_count"] == 1


# ---------------------------------------------------------------------------
# Test 3: record_rejection() increments rejected_count
# ---------------------------------------------------------------------------

def test_record_rejection_increments_rejected_count():
    """record_rejection increments rejected_count for the given domain."""
    tracker = make_tracker()
    tracker.record_recommendation("flock_anomaly", "rec-001")
    tracker.record_rejection("flock_anomaly")
    state = tracker.get_maturity_state("flock_anomaly")
    assert state["rejected_count"] == 1


# ---------------------------------------------------------------------------
# Test 4: get_maturity_state() returns dict with correct keys and approval_rate
# ---------------------------------------------------------------------------

def test_get_maturity_state_returns_correct_keys_and_approval_rate():
    """get_maturity_state returns dict with all required fields and correct approval_rate."""
    tracker = make_tracker()
    tracker.record_recommendation("irrigation", "rec-001")
    tracker.record_recommendation("irrigation", "rec-002")
    tracker.record_recommendation("irrigation", "rec-003")
    tracker.record_approval("irrigation")
    tracker.record_approval("irrigation")
    tracker.record_rejection("irrigation")

    state = tracker.get_maturity_state("irrigation")

    assert "domain" in state
    assert "recommendation_count" in state
    assert "approved_count" in state
    assert "rejected_count" in state
    assert "approval_rate" in state

    assert state["domain"] == "irrigation"
    assert state["recommendation_count"] == 3
    assert state["approved_count"] == 2
    assert state["rejected_count"] == 1
    assert state["approval_rate"] == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# Test 5: get_all_maturity_states() returns all 3 domain entries
# ---------------------------------------------------------------------------

def test_get_all_maturity_states_returns_all_domains():
    """get_all_maturity_states returns a list of 3 dicts (one per domain)."""
    tracker = make_tracker()
    states = tracker.get_all_maturity_states()

    assert isinstance(states, list)
    assert len(states) == 3

    domain_names = {s["domain"] for s in states}
    assert "irrigation" in domain_names
    assert "zone_health" in domain_names
    assert "flock_anomaly" in domain_names


# ---------------------------------------------------------------------------
# Test 6: approval_rate is 0.0 when recommendation_count is 0 (no division by zero)
# ---------------------------------------------------------------------------

def test_approval_rate_zero_when_no_recommendations():
    """approval_rate is 0.0 when recommendation_count is 0 — no ZeroDivisionError."""
    tracker = make_tracker()
    state = tracker.get_maturity_state("irrigation")
    assert state["recommendation_count"] == 0
    assert state["approval_rate"] == 0.0


# ---------------------------------------------------------------------------
# Test 7: load_from_db / persist_to_db round-trip (mock db_pool)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_from_db_and_persist_round_trip():
    """load_from_db populates internal state from DB rows; persist_to_db writes back."""
    pool = make_db_pool()
    tracker = MaturityTracker(pool)

    # Simulate DB returning rows for all 3 domains
    pool.fetch.return_value = [
        {
            "domain": "irrigation",
            "recommendation_count": 10,
            "approved_count": 7,
            "rejected_count": 3,
        },
        {
            "domain": "zone_health",
            "recommendation_count": 5,
            "approved_count": 4,
            "rejected_count": 1,
        },
        {
            "domain": "flock_anomaly",
            "recommendation_count": 2,
            "approved_count": 1,
            "rejected_count": 1,
        },
    ]

    await tracker.load_from_db()

    # Verify state was populated from DB
    irrigation_state = tracker.get_maturity_state("irrigation")
    assert irrigation_state["recommendation_count"] == 10
    assert irrigation_state["approved_count"] == 7
    assert irrigation_state["rejected_count"] == 3

    # Now call persist_to_db and verify execute was called for each domain
    await tracker.persist_to_db()

    # Should have called execute at least once for the upsert
    assert pool.execute.called, "persist_to_db should call db_pool.execute"
    # Verify at least one of the calls contains 'model_maturity' table reference
    execute_calls_sql = [str(c) for c in pool.execute.call_args_list]
    all_sql = " ".join(execute_calls_sql)
    assert "model_maturity" in all_sql, (
        "persist_to_db should write to model_maturity table"
    )
