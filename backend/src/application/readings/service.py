from collections.abc import Callable
from uuid import UUID

from application.readings.dto import ReadingDto
from application.readings.mappers import reading_to_dto
from domain.devices.entity import Device
from domain.devices.errors import DeviceNotFoundError
from domain.sensors.ports import SensorPort
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

# Der Service bekommt nur eine Funktion "Device -> SensorPort".
# So kennt er keine konkrete Adapter-Klasse.
AdapterSelector = Callable[[Device], SensorPort]


class ReadingService:
    """Use Case: Geraet laden -> Adapter waehlen -> lesen -> speichern -> DTO."""

    def __init__(
        self,
        devices: DeviceRepository,
        readings: ReadingRepository,
        select_adapter: AdapterSelector,
    ):
        self._devices = devices
        self._readings = readings
        self._select_adapter = select_adapter

    def take_reading(self, device_id: UUID) -> ReadingDto:
        device = self._load_device(device_id)
        port = self._select_adapter(device)
        reading = port.read(device)  # SensorReadError geht unveraendert weiter
        return reading_to_dto(self._readings.insert(reading))

    def list_readings(self, device_id: UUID, limit: int = 20) -> list[ReadingDto]:
        self._load_device(device_id)
        return [reading_to_dto(r) for r in self._readings.list_for_device(device_id, limit)]

    def _load_device(self, device_id: UUID) -> Device:
        device = self._devices.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device {device_id} not found")
        return device
