from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from application.sensors.service import SensorService
from infrastructure.db import get_db
from infrastructure.persistence.device_repository import DeviceRepository

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


class CreateSensorRequest(BaseModel):
    type: str  # Creator-Schluessel: "moisture" | "light"
    display_name: str | None = None


class SensorResponse(BaseModel):
    id: UUID
    device_type: str
    display_name: str | None
    default_config: dict


def get_service(db: Session = Depends(get_db)) -> SensorService:
    return SensorService(DeviceRepository(db))


@router.get("", response_model=list[SensorResponse])
def list_sensors(service: SensorService = Depends(get_service)) -> list[SensorResponse]:
    return [SensorResponse(**vars(s)) for s in service.list_sensors()]


@router.post("", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
def create_sensor(
    body: CreateSensorRequest,
    service: SensorService = Depends(get_service),
) -> SensorResponse:
    try:
        sensor = service.create_sensor(body.type, body.display_name)
    except ValueError as exc:
        # Unbekannter Typ wird schon im Domain-Layer abgelehnt -> 400.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SensorResponse(**vars(sensor))
