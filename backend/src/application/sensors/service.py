from domain.sensors.creators import get_creator
from domain.sensors.entity import Sensor
from infrastructure.persistence.device_repository import DeviceRepository


class SensorService:
    """Verbindet Creator (Factory Method) mit dem Repository."""

    def __init__(self, repo: DeviceRepository):
        self._repo = repo

    def create_sensor(self, sensor_type: str, display_name: str | None = None) -> Sensor:
        # Creator baut den Prototyp, Repository persistiert ihn.
        creator = get_creator(sensor_type)
        prototype = creator.create_sensor(display_name=display_name)
        return self._repo.save_sensor(prototype)

    def list_sensors(self) -> list[Sensor]:
        return self._repo.list_sensors()
