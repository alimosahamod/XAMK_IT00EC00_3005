from domain.devices.entity import Device
from domain.devices.family_factory import get_family_factory
from infrastructure.persistence.device_repository import DeviceRepository


class DeviceFamilyService:
    """Verbindet die Abstract Factory mit dem Repository.

    Der Service arbeitet nur mit Domain-Devices. Die DTOs entstehen erst im
    Router, damit die Anwendungslogik unabhaengig von HTTP bleibt.
    """

    def __init__(self, repo: DeviceRepository):
        self._repo = repo

    def provision_family(self, family: str) -> list[Device]:
        # Die Factory entscheidet, welche Geraete zusammengehoeren.
        # Ein unbekannter Familienname fuehrt hier zu einem ValueError.
        factory = get_family_factory(family)
        return self._repo.save_devices(factory.create_device_set())

    def list_devices(
        self,
        *,
        device_family: str | None = None,
        role: str | None = None,
    ) -> list[Device]:
        return self._repo.list_devices(device_family=device_family, role=role)
