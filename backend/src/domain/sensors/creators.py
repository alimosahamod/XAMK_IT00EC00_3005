from abc import ABC, abstractmethod

from domain.sensors.entity import Sensor


class SensorCreator(ABC):
    """Abstrakter Creator: die Factory Method ist create_sensor."""

    @abstractmethod
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        ...


class MoistureSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        # Feuchtigkeitssensor: Einheit vwc + eigener Schwellwert.
        return Sensor(
            device_type="moisture_sensor",
            display_name=display_name or "Soil moisture sensor",
            default_config={
                "unit": "vwc",
                "sampling_interval_seconds": 300,
                "moisture_threshold": 30,
            },
        )


class LightSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        # Lichtsensor: andere Einheit (lux) und anderes Intervall.
        return Sensor(
            device_type="light_sensor",
            display_name=display_name or "Light sensor",
            default_config={
                "unit": "lux",
                "sampling_interval_seconds": 60,
            },
        )


# Registry: kurzer Typ-Schluessel -> passender Creator.
_CREATORS: dict[str, SensorCreator] = {
    "moisture": MoistureSensorCreator(),
    "light": LightSensorCreator(),
}


def get_creator(sensor_type: str) -> SensorCreator:
    """Waehlt den Creator per Schluessel; unbekannter Typ -> ValueError."""
    try:
        return _CREATORS[sensor_type]
    except KeyError:
        raise ValueError(f"Unknown sensor type: {sensor_type}")
