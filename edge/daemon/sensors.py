"""Sensor drivers for edge node.

DS18B20 (temperature): 1-Wire bus via w1thermsensor library (D-03).
ADS1115 (pH): I2C ADC via adafruit-circuitpython-ads1x15 (D-02).
Moisture: Placeholder — sensor model TBD per D-01 research spike.
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SensorDriver(ABC):
    """Abstract base class for sensor drivers."""

    @abstractmethod
    def read(self) -> float:
        """Read sensor value. Returns None if read fails."""
        ...

    @abstractmethod
    def sensor_type(self) -> str:
        """Return sensor type string matching MQTT topic."""
        ...


class DS18B20Driver(SensorDriver):
    """DS18B20 temperature sensor via 1-Wire bus."""

    def __init__(self, sensor_id: str = None):
        self._sensor = None
        self._sensor_id = sensor_id
        try:
            from w1thermsensor import W1ThermSensor, Unit
            if sensor_id:
                self._sensor = W1ThermSensor(sensor_id=sensor_id)
            else:
                self._sensor = W1ThermSensor()  # first found
            self._unit = Unit.DEGREES_C
            logger.info("DS18B20 initialized: %s", self._sensor.id)
        except Exception as e:
            logger.error("DS18B20 init failed: %s", e)

    def read(self) -> float:
        if self._sensor is None:
            return None
        try:
            return round(self._sensor.get_temperature(self._unit), 1)
        except Exception as e:
            logger.error("DS18B20 read error: %s", e)
            return None

    def sensor_type(self) -> str:
        return "temperature"


class ADS1115PHDriver(SensorDriver):
    """pH sensor via ADS1115 16-bit ADC on I2C bus."""

    def __init__(self, i2c_address: int = 0x48, channel: int = 0, gain: float = 1):
        self._adc = None
        self._channel = None
        try:
            import board
            import busio
            import adafruit_ads1x15.ads1115 as ADS
            from adafruit_ads1x15.analog_in import AnalogIn
            i2c = busio.I2C(board.SCL, board.SDA)
            self._adc = ADS.ADS1115(i2c, address=i2c_address, gain=gain)
            self._channel = AnalogIn(self._adc, channel)
            logger.info("ADS1115 pH initialized at 0x%02x channel %d", i2c_address, channel)
        except Exception as e:
            logger.error("ADS1115 pH init failed: %s", e)

    def read(self) -> float:
        if self._channel is None:
            return None
        try:
            voltage = self._channel.voltage
            # Linear pH conversion: pH 7.0 at 0V offset, ~0.18V per pH unit
            # Calibration offsets are applied at hub ingestion (ZONE-03), not here
            ph = 7.0 + (voltage - 2.5) / -0.18
            return round(ph, 2)
        except Exception as e:
            logger.error("ADS1115 pH read error: %s", e)
            return None

    def sensor_type(self) -> str:
        return "ph"


class MoisturePlaceholder(SensorDriver):
    """Placeholder moisture driver — sensor model TBD per D-01.

    Replace this class once moisture sensor hardware is selected.
    Currently returns None for all reads.
    """

    def read(self) -> float:
        logger.warning("Moisture sensor not configured — D-01 research spike pending")
        return None

    def sensor_type(self) -> str:
        return "moisture"
