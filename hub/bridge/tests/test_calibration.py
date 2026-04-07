import pytest
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
