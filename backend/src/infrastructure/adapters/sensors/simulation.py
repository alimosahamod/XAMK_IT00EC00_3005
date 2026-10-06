import random
from collections.abc import Callable
from datetime import UTC, datetime

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading

# Plausible Wertebereiche pro Sensortyp: (min, max, Einheit).
_RANGES: dict[str, tuple[float, float, str]] = {
    "moisture_sensor": (0.15, 0.45, "vwc"),
    "light_sensor": (200.0, 20000.0, "lux"),
}


class SimulationSensorAdapter(SensorPort):
    """Erzeugt plausible Zufallswerte, ohne echte Hardware.

    Zufall und Uhr sind injizierbar, damit Tests feste Werte bekommen.
    """

    def __init__(
        self,
        rng: random.Random | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        self._rng = rng or random.Random()
        self._clock = clock or (lambda: datetime.now(UTC))

    def read(self, device: Device) -> Reading:
        if device.id is None:
            raise SensorReadError("Cannot read an unsaved device")
        try:
            low, high, unit = _RANGES[device.device_type]
        except KeyError:
            raise SensorReadError(f"Simulation cannot read device type: {device.device_type}")
        return Reading(
            device_id=device.id,
            value=round(self._rng.uniform(low, high), 4),
            unit=unit,
            source="simulation",
            recorded_at=self._clock(),
        )
