import pytest
from datetime import datetime, timedelta, timezone
from calibration import CalibrationStore


def test_apply_offset():
    store = CalibrationStore()
    store.set_offset("zone-01", "moisture", 2.5)
    value, applied = store.apply_calibration("zone-01", "moisture", 40.0)
    assert value == 42.5
    assert applied is True


def test_no_calibration_record():
    store = CalibrationStore()
    value, applied = store.apply_calibration("zone-01", "moisture", 40.0)
    assert value == 40.0
    assert applied is False


def test_zero_offset():
    store = CalibrationStore()
    store.set_offset("zone-01", "ph", 0.0)
    value, applied = store.apply_calibration("zone-01", "ph", 6.8)
    assert value == 6.8
    assert applied is True


def test_negative_offset():
    store = CalibrationStore()
    store.set_offset("zone-02", "temperature", -1.5)
    value, applied = store.apply_calibration("zone-02", "temperature", 23.5)
    assert value == 22.0
    assert applied is True


# --- Phase 5: CalibrationStore overdue detection tests ---

class TestCalibrationOverdue:
    def test_is_overdue_when_never_calibrated(self):
        """is_overdue returns True when no calibration date recorded."""
        store = CalibrationStore()
        store.set_offset("zone-01", "ph", 0.0)
        assert store.is_overdue("zone-01", "ph") is True

    def test_is_overdue_when_calibration_old(self):
        """is_overdue returns True when last calibration was 15 days ago."""
        store = CalibrationStore()
        store.set_offset("zone-01", "ph", 0.0)
        store._calibration_dates[("zone-01", "ph")] = datetime.now(timezone.utc) - timedelta(days=15)
        assert store.is_overdue("zone-01", "ph") is True

    def test_not_overdue_when_recent(self):
        """is_overdue returns False when last calibration was 5 days ago."""
        store = CalibrationStore()
        store.set_offset("zone-01", "ph", 0.0)
        store._calibration_dates[("zone-01", "ph")] = datetime.now(timezone.utc) - timedelta(days=5)
        assert store.is_overdue("zone-01", "ph") is False

    def test_not_overdue_at_exactly_14_days(self):
        """is_overdue returns False at exactly 14 days (overdue is strictly >14 days)."""
        store = CalibrationStore()
        store.set_offset("zone-01", "ph", 0.0)
        store._calibration_dates[("zone-01", "ph")] = datetime.now(timezone.utc) - timedelta(days=14)
        assert store.is_overdue("zone-01", "ph") is False

    def test_get_all_calibrations_returns_all_fields(self):
        """get_all_calibrations returns dicts with all expected fields."""
        store = CalibrationStore()
        store._offsets[("zone-01", "ph")] = 0.1
        store._dry_values[("zone-01", "ph")] = 100.0
        store._wet_values[("zone-01", "ph")] = 500.0
        store._temp_coefficients[("zone-01", "ph")] = 0.02
        store._calibration_dates[("zone-01", "ph")] = datetime.now(timezone.utc) - timedelta(days=3)

        calibrations = store.get_all_calibrations()
        assert len(calibrations) == 1
        cal = calibrations[0]
        assert cal["zone_id"] == "zone-01"
        assert cal["sensor_type"] == "ph"
        assert cal["offset_value"] == 0.1
        assert cal["dry_value"] == 100.0
        assert cal["wet_value"] == 500.0
        assert cal["temp_coefficient"] == 0.02
        assert "last_calibration_date" in cal
        assert "days_since_calibration" in cal
        assert cal["days_since_calibration"] == pytest.approx(3, abs=0.1)
