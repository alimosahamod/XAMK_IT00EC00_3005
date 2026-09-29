from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from application.devices.dto import DeviceDto
from application.devices.family_service import DeviceFamilyService
from application.devices.mappers import devices_to_dtos
from infrastructure.db import get_db
from infrastructure.persistence.device_repository import DeviceRepository

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_service(db: Session = Depends(get_db)) -> DeviceFamilyService:
    return DeviceFamilyService(DeviceRepository(db))


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
