from collections.abc import Callable
from uuid import UUID

from application.readings.dto import ReadingDto
from application.readings.mappers import reading_to_dto
from domain.devices.entity import Device
from domain.devices.errors import DeviceNotFoundError
from domain.events.bus import EventBus
from domain.events.events import ReadingCreated
from domain.sensors.ports import SensorPort
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

# Der Service bekommt nur eine Funktion "Device -> SensorPort".
# So kennt er keine konkrete Adapter-Klasse.
AdapterSelector = Callable[[Device], SensorPort]


class ReadingService:
    """Use Case: Geraet laden -> Adapter waehlen -> lesen -> speichern -> publizieren -> DTO.

    Phase 11: einziger Ingest-Pfad und damit einziger Publisher von
    `reading.created`. Er kennt nur den EventBus, keine Alarme.
    """

    def __init__(
        self,
        devices: DeviceRepository,
        readings: ReadingRepository,
        select_adapter: AdapterSelector,
        bus: EventBus,
    ):
        self._devices = devices
        self._readings = readings
        self._select_adapter = select_adapter
        self._bus = bus

    def take_reading(self, device_id: UUID) -> ReadingDto:
        device = self._load_device(device_id)
        port = self._select_adapter(device)
        reading = port.read(device)  # SensorReadError geht unveraendert weiter
        stored = self._readings.insert(reading)

        # Erst NACH dem Speichern publizieren, und nur wenn das Geraet getrackt wird.
        # Bei tracking_enabled=false bleibt die Zeile gespeichert, es gibt nur kein Event.
        if device.tracking_enabled:
            self._bus.publish(
                ReadingCreated(
                    device_id=stored.device_id,
                    value=stored.value,
                    unit=stored.unit,
                    source=stored.source,
                    recorded_at=stored.recorded_at,
                    # Vom Geraet kopiert; nicht zugewiesen -> beide None.
                    location_id=device.location_id,
                    zone_id=device.zone_id,
                )
            )
        return reading_to_dto(stored)

    def list_readings(self, device_id: UUID, limit: int = 20) -> list[ReadingDto]:
        self._load_device(device_id)
        return [reading_to_dto(r) for r in self._readings.list_for_device(device_id, limit)]

    def _load_device(self, device_id: UUID) -> Device:
        device = self._devices.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device {device_id} not found")
        return device
