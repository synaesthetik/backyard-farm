"""Tests for alert_engine.py — alert evaluation with debounce and hysteresis."""
import pytest

from alert_engine import AlertEngine


class TestAlertEngineFire:
    def test_fires_on_threshold_crossing(self):
        """Alert fires when value drops below threshold."""
        engine = AlertEngine()
        changed, is_active = engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        assert changed is True
        assert is_active is True

    def test_stays_active_during_sustained_condition(self):
        """Second evaluation with same low value: changed=False, is_active=True."""
        engine = AlertEngine()
        engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        changed, is_active = engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        assert changed is False
        assert is_active is True

    def test_no_alert_when_above_threshold(self):
        """Value above threshold — no alert fires."""
        engine = AlertEngine()
        changed, is_active = engine.evaluate("moisture_low:zone-01", 35.0, fire_threshold=20.0)
        assert changed is False
        assert is_active is False


class TestAlertEngineHysteresis:
    def test_does_not_clear_within_hysteresis(self):
        """Alert stays active when value recovers to threshold+hysteresis but not beyond."""
        engine = AlertEngine()
        # Fire the alert
        engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        # Recover to 22 — within hysteresis band (threshold=20, hysteresis=5, clear_above=25)
        changed, is_active = engine.evaluate("moisture_low:zone-01", 22.0, fire_threshold=20.0)
        assert changed is False
        assert is_active is True

    def test_clears_past_hysteresis(self):
        """Alert clears when value recovers past threshold + hysteresis band."""
        engine = AlertEngine()
        # Fire
        engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        # Recover to 26 — beyond hysteresis band (threshold=20, hysteresis=5, clear_above=25)
        changed, is_active = engine.evaluate("moisture_low:zone-01", 26.0, fire_threshold=20.0)
        assert changed is True
        assert is_active is False

    def test_re_fires_after_clearing(self):
        """Alert can re-fire after it has been cleared."""
        engine = AlertEngine()
        engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        engine.evaluate("moisture_low:zone-01", 26.0, fire_threshold=20.0)
        # Drop below threshold again
        changed, is_active = engine.evaluate("moisture_low:zone-01", 10.0, fire_threshold=20.0)
        assert changed is True
        assert is_active is True


class TestAlertEngineHighThreshold:
    def test_fires_on_high_threshold_crossing(self):
        """Alert fires when value rises above threshold (clear_above=False)."""
        engine = AlertEngine()
        changed, is_active = engine.evaluate(
            "ph_high:zone-01", 8.0, fire_threshold=7.5, clear_above=False
        )
        assert changed is True
        assert is_active is True

    def test_clears_past_hysteresis_for_high(self):
        """ph_high alert clears when value drops below threshold - hysteresis."""
        engine = AlertEngine()
        engine.evaluate("ph_high:zone-01", 8.0, fire_threshold=7.5, clear_above=False)
        # ph hysteresis is 0.2, so clear when value < 7.5 - 0.2 = 7.3
        changed, is_active = engine.evaluate(
            "ph_high:zone-01", 7.2, fire_threshold=7.5, clear_above=False
        )
        assert changed is True
        assert is_active is False

    def test_does_not_clear_within_hysteresis_for_high(self):
        """ph_high stays active while within hysteresis band."""
        engine = AlertEngine()
        engine.evaluate("ph_high:zone-01", 8.0, fire_threshold=7.5, clear_above=False)
        # Recover to 7.35 — within hysteresis band (threshold=7.5, hysteresis=0.2, clear_below=7.3)
        changed, is_active = engine.evaluate(
            "ph_high:zone-01", 7.35, fire_threshold=7.5, clear_above=False
        )
        assert changed is False
        assert is_active is True


class TestAlertEngineDirectSet:
    def test_set_alert_activates(self):
        engine = AlertEngine()
        engine.set_alert("stuck_door:coop")
        state = engine.get_alert_state()
        assert any(a["key"].startswith("stuck_door") for a in state)

    def test_clear_alert_deactivates(self):
        engine = AlertEngine()
        engine.set_alert("stuck_door:coop")
        engine.clear_alert("stuck_door:coop")
        state = engine.get_alert_state()
        assert not any(a["key"].startswith("stuck_door") for a in state)


class TestAlertEngineGrouping:
    def test_get_alert_state_returns_grouped_alerts(self):
        """Two moisture_low alerts for different zones grouped with count=2."""
        engine = AlertEngine()
        engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        engine.evaluate("moisture_low:zone-02", 15.0, fire_threshold=20.0)
        state = engine.get_alert_state()
        grouped = [a for a in state if "moisture_low" in a["key"]]
        assert len(grouped) == 1
        assert grouped[0]["count"] == 2

    def test_single_alert_not_grouped(self):
        """Single moisture_low alert has count=1 and zone-specific key."""
        engine = AlertEngine()
        engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        state = engine.get_alert_state()
        moisture_alerts = [a for a in state if "moisture_low" in a["key"]]
        assert len(moisture_alerts) == 1
        assert moisture_alerts[0]["count"] == 1
        assert "zone-01" in moisture_alerts[0]["key"]

    def test_p0_alerts_sorted_before_p1(self):
        """P0 severity alerts appear before P1 in get_alert_state output."""
        engine = AlertEngine()
        engine.evaluate("moisture_low:zone-01", 15.0, fire_threshold=20.0)
        engine.set_alert("stuck_door:coop")
        state = engine.get_alert_state()
        severities = [a["severity"] for a in state]
        p0_idx = next((i for i, s in enumerate(severities) if s == "P0"), None)
        p1_idx = next((i for i, s in enumerate(severities) if s == "P1"), None)
        if p0_idx is not None and p1_idx is not None:
            assert p0_idx < p1_idx
