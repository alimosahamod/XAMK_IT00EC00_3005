from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from application.readings.dto import ReadingDto
from application.readings.service import ReadingService
from application.sensors.service import SensorService
from domain.devices.errors import DeviceNotFoundError
from domain.sensors.errors import SensorReadError
from infrastructure.adapters.sensors.selector import select_sensor_adapter
from infrastructure.db import get_db
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

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


# --- Phase 5: Messwerte lesen (Adapter) ------------------------------------


def get_reading_service(db: Session = Depends(get_db)) -> ReadingService:
    # Hier wird der Selector eingesteckt; der Router selbst kennt keine Adapter.
    return ReadingService(DeviceRepository(db), ReadingRepository(db), select_sensor_adapter)


@router.post(
    "/{device_id}/read",
    response_model=ReadingDto,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Device not found"}, 400: {"description": "Read failed"}},
)
def read_sensor(
    device_id: UUID,
    service: ReadingService = Depends(get_reading_service),
) -> ReadingDto:
    """Liest den Sensor ueber seinen Adapter und speichert den Wert."""
    try:
        return service.take_reading(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SensorReadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/{device_id}/readings",
    response_model=list[ReadingDto],
    responses={404: {"description": "Device not found"}},
)
def list_readings(
    device_id: UUID,
    limit: int = Query(default=20, ge=1, le=100, description="Newest readings first"),
    service: ReadingService = Depends(get_reading_service),
) -> list[ReadingDto]:
    """Gespeicherte Messwerte, neueste zuerst (limit=1 liefert den aktuellen)."""
    try:
        return service.list_readings(device_id, limit)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
