from application.devices.dto import DeviceDto
from domain.actuators.context import ActuatorContext
from domain.devices.entity import Device


def device_to_dto(device: Device) -> DeviceDto:
    """Wandelt ein gespeichertes Domain-Device in das API-Lesemodell um."""
    if device.id is None:
        # Ohne id ist das Device noch nicht persistiert und gehoert nicht in eine Antwort.
        raise ValueError("Cannot map an unpersisted device to a DTO")
    # Die erlaubten Befehle kommen aus dem Zustandsobjekt, nicht aus einem if hier.
    allowed = ActuatorContext(device.state).allowed_commands() if device.state else []
    return DeviceDto(
        id=device.id,
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=device.default_config,
        state=device.state,
        allowed_commands=allowed,
    )


def devices_to_dtos(devices: list[Device]) -> list[DeviceDto]:
    return [device_to_dto(device) for device in devices]
