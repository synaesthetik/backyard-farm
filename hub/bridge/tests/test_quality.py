from quality import apply_quality_flag, StuckDetector
from models import QualityFlag


class TestMoistureFlags:
    def test_good_moisture_reading(self):
        assert apply_quality_flag("moisture", 42.3) == QualityFlag.GOOD

    def test_bad_moisture_below_zero(self):
        assert apply_quality_flag("moisture", -1.0) == QualityFlag.BAD

    def test_bad_moisture_above_100(self):
        assert apply_quality_flag("moisture", 101.0) == QualityFlag.BAD

    def test_suspect_moisture_low(self):
        assert apply_quality_flag("moisture", 1.5) == QualityFlag.SUSPECT

    def test_suspect_moisture_high(self):
        assert apply_quality_flag("moisture", 99.0) == QualityFlag.SUSPECT

    def test_good_moisture_at_boundary(self):
        assert apply_quality_flag("moisture", 2.0) == QualityFlag.GOOD
        assert apply_quality_flag("moisture", 98.0) == QualityFlag.GOOD


class TestPHFlags:
    def test_good_ph(self):
        assert apply_quality_flag("ph", 6.8) == QualityFlag.GOOD

    def test_bad_ph_below_zero(self):
        assert apply_quality_flag("ph", -0.5) == QualityFlag.BAD

    def test_suspect_ph_low(self):
        assert apply_quality_flag("ph", 2.5) == QualityFlag.SUSPECT

    def test_good_ph_at_boundary(self):
        assert apply_quality_flag("ph", 3.0) == QualityFlag.GOOD
        assert apply_quality_flag("ph", 10.0) == QualityFlag.GOOD


class TestTemperatureFlags:
    def test_good_temperature(self):
        assert apply_quality_flag("temperature", 22.0) == QualityFlag.GOOD

    def test_bad_temperature_below(self):
        assert apply_quality_flag("temperature", -15.0) == QualityFlag.BAD

    def test_suspect_temperature_high(self):
        assert apply_quality_flag("temperature", 65.0) == QualityFlag.SUSPECT


class TestUnknownSensor:
    def test_unknown_sensor_defaults_good(self):
        assert apply_quality_flag("feed_weight", 500.0) == QualityFlag.GOOD


class TestStuckDetector:
    def test_not_stuck_at_29(self):
        detector = StuckDetector(threshold=30)
        for _ in range(29):
            result = detector.check("zone-01", "moisture", 42.3)
        assert result is False

    def test_stuck_at_30(self):
        detector = StuckDetector(threshold=30)
        for i in range(30):
            result = detector.check("zone-01", "moisture", 42.3)
        assert result is True

    def test_stuck_resets_on_different_value(self):
        detector = StuckDetector(threshold=30)
        for _ in range(30):
            detector.check("zone-01", "moisture", 42.3)
        result = detector.check("zone-01", "moisture", 42.4)
        assert result is False

    def test_separate_sensors_tracked_independently(self):
        detector = StuckDetector(threshold=30)
        for _ in range(30):
            detector.check("zone-01", "moisture", 42.3)
            detector.check("zone-01", "ph", 6.8)
        # moisture is stuck, but we check ph with only 30 readings
        assert detector.check("zone-01", "moisture", 42.3) is True
        assert detector.check("zone-01", "ph", 7.0) is False
