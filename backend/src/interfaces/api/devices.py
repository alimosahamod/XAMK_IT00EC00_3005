from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from application.devices.dto import DeviceDto, TransitionRequestDto
from application.devices.family_service import DeviceFamilyService
from application.devices.mappers import device_to_dto, devices_to_dtos
from application.devices.state_service import ActuatorStateService
from domain.actuators.errors import IllegalTransitionError
from domain.devices.errors import DeviceNotFoundError
from domain.events.bus import EventBus
from infrastructure.db import get_db
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.device_repository import DeviceRepository
from interfaces.api.event_bus import get_event_bus

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_service(db: Session = Depends(get_db)) -> DeviceFamilyService:
    return DeviceFamilyService(DeviceRepository(db))


def get_state_service(
    db: Session = Depends(get_db), bus: EventBus = Depends(get_event_bus)
) -> ActuatorStateService:
    return ActuatorStateService(DeviceRepository(db), ActuatorStateRepository(db), bus)


@router.get("", response_model=list[DeviceDto])
def list_devices(
    family: str | None = Query(default=None, description="Filter by device family"),
    role: str | None = Query(default=None, description="Filter by role: sensor or actuator"),
    service: DeviceFamilyService = Depends(get_service),
) -> list[DeviceDto]:
    devices = service.list_devices(device_family=family, role=role)
    # Der Router mappt genau einmal vom Domain-Objekt auf das DTO.
    return devices_to_dtos(devices)


@router.post("/provision", response_model=list[DeviceDto], status_code=status.HTTP_201_CREATED)
def provision_family(
    family: str = Query(description="Device family to provision: simulation or edge"),
    service: DeviceFamilyService = Depends(get_service),
) -> list[DeviceDto]:
    """Legt ein komplettes Geraeteset der Familie an (Familie als Query-Parameter)."""
    try:
        devices = service.provision_family(family)
    except ValueError as exc:
        # Unbekannte Familie wird in der Domain abgelehnt -> 400.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return devices_to_dtos(devices)


@router.post(
    "/{device_id}/transition",
    response_model=DeviceDto,
    responses={
        404: {"description": "Actuator not found"},
        409: {"description": "Transition not allowed from the current state"},
    },
)
def transition_actuator(
    device_id: UUID,
    body: TransitionRequestDto,
    service: ActuatorStateService = Depends(get_state_service),
) -> DeviceDto:
    """Wechselt den Zustand eines Aktuators (Demo; ab Phase 10 ueber Command).

    Der Router kennt keine Uebergangsregeln, er uebersetzt nur Domain-Fehler in HTTP.
    """
    try:
        return device_to_dto(service.transition(device_id, body.target))
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
