"""Tests for rule_engine.py — threshold-based recommendation engine."""
import types
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from rule_engine import RuleEngine


def make_zone_config(vwc_low=30.0, vwc_high=60.0):
    return types.SimpleNamespace(
        vwc_low_threshold=vwc_low,
        vwc_high_threshold=vwc_high,
    )


class TestRuleEngineThreshold:
    def test_emits_recommendation_when_below_threshold(self):
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec is not None
        assert rec["zone_id"] == "zone-01"
        assert rec["action_description"] is not None
        assert rec["sensor_reading"] is not None
        assert rec["explanation"] is not None
        assert "recommendation_id" in rec

    def test_no_recommendation_when_above_threshold(self):
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec = engine.evaluate_zone("zone-01", "moisture", 45.0, config)
        assert rec is None

    def test_non_moisture_sensor_returns_none(self):
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec = engine.evaluate_zone("zone-01", "ph", 5.0, config)
        assert rec is None


class TestRuleEngineDedup:
    def test_suppresses_duplicate_when_pending(self):
        """AI-04: second call with same low moisture returns None while first is pending."""
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec1 = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec1 is not None
        rec2 = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec2 is None

    def test_emits_for_different_zones_independently(self):
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec1 = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        rec2 = engine.evaluate_zone("zone-02", "moisture", 20.0, config)
        assert rec1 is not None
        assert rec2 is not None


class TestRuleEngineBackoff:
    def test_suppresses_during_backoff(self):
        """AI-05: reject recommendation, call again within backoff window -> None."""
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec is not None
        engine.reject(rec["recommendation_id"])
        # Immediately try again — should be in backoff window
        rec2 = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec2 is None

    def test_allows_after_backoff_expires(self):
        """AI-05: after backoff window expires, new recommendation is generated."""
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec is not None
        engine.reject(rec["recommendation_id"])

        # Simulate time passing beyond backoff window by patching rejected_at
        key = "zone-01:irrigate"
        past_time = datetime.now(timezone.utc) - timedelta(minutes=61)
        engine._recommendations[key].rejected_at = past_time

        rec2 = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec2 is not None


class TestRuleEngineCooldown:
    def test_suppresses_during_cooldown(self):
        """IRRIG-06: record irrigation event, call within cooldown -> None."""
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        engine.record_irrigation_complete("zone-01")
        rec = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec is None

    def test_allows_after_cooldown_expires(self):
        """IRRIG-06: after cooldown window expires, new recommendation is generated."""
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        engine.record_irrigation_complete("zone-01")
        # Simulate time passing beyond cooldown by backdating last_irrigated
        past_time = datetime.now(timezone.utc) - timedelta(minutes=121)
        engine._last_irrigated["zone-01"] = past_time
        rec = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        assert rec is not None

    def test_cooldown_specific_to_zone(self):
        """Cooldown on zone-01 does not affect zone-02."""
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        engine.record_irrigation_complete("zone-01")
        rec = engine.evaluate_zone("zone-02", "moisture", 20.0, config)
        assert rec is not None


class TestRuleEnginePendingList:
    def test_get_pending_recommendations_returns_list(self):
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        pending = engine.get_pending_recommendations()
        assert len(pending) == 1
        assert pending[0]["zone_id"] == "zone-01"

    def test_approve_removes_from_pending(self):
        engine = RuleEngine()
        config = make_zone_config(vwc_low=30.0, vwc_high=60.0)
        rec = engine.evaluate_zone("zone-01", "moisture", 20.0, config)
        engine.approve(rec["recommendation_id"])
        pending = engine.get_pending_recommendations()
        assert len(pending) == 0
