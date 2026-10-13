from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from application.automation.dto import (
    AutomationRuleDto,
    RecommendationDto,
    SetStrategyRequestDto,
)
from application.automation.service import AutomationService
from domain.automation.errors import (
    AutomationNotReadyError,
    LocationNotFoundError,
    SensorLinkError,
    UnknownStrategyError,
)
from domain.automation.strategy import available_keys
from domain.devices.errors import DeviceNotFoundError
from infrastructure.db import get_db
from infrastructure.persistence.automation_repository import AutomationRuleRepository
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.location_repository import LocationRepository
from infrastructure.persistence.reading_repository import ReadingRepository

router = APIRouter(tags=["automation"])


def get_service(db: Session = Depends(get_db)) -> AutomationService:
    return AutomationService(
        AutomationRuleRepository(db),
        LocationRepository(db),
        ReadingRepository(db),
        DeviceRepository(db),
    )


@router.get("/api/automation/strategies", response_model=list[str])
def list_strategies() -> list[str]:
    """Alle bekannten strategy_keys, z.B. fuer das Dropdown."""
    return available_keys()


@router.get(
    "/api/locations/{location_id}/automation",
    response_model=AutomationRuleDto,
    responses={404: {"description": "Location not found"}},
)
def get_automation(
    location_id: UUID,
    service: AutomationService = Depends(get_service),
) -> AutomationRuleDto:
    """Gespeicherte Strategie des Standorts (strategy_key ist null, wenn keine gewaehlt ist)."""
    try:
        return service.get_rule(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put(
    "/api/locations/{location_id}/automation",
    response_model=AutomationRuleDto,
    responses={404: {"description": "Location not found"}, 400: {"description": "Unknown key"}},
)
def set_automation(
    location_id: UUID,
    body: SetStrategyRequestDto,
    service: AutomationService = Depends(get_service),
) -> AutomationRuleDto:
    """Speichert die aktive Strategie des Standorts (Upsert)."""
    try:
        return service.set_strategy(location_id, body.strategy_key)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnknownStrategyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/api/locations/{location_id}/automation/evaluate",
    response_model=RecommendationDto,
    responses={
        404: {"description": "Location not found"},
        400: {"description": "Saved key is unknown"},
        409: {"description": "No strategy, zone or moisture reading yet"},
    },
)
def evaluate_automation(
    location_id: UUID,
    service: AutomationService = Depends(get_service),
) -> RecommendationDto:
    """Wertet die gespeicherte Strategie mit dem neuesten Feuchtewert und den Zonen aus."""
    try:
        return service.evaluate(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnknownStrategyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except AutomationNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.put(
    "/api/locations/{location_id}/sensors/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Location or device not found"},
        400: {"description": "Not a moisture sensor"},
    },
)
def link_sensor(
    location_id: UUID,
    device_id: UUID,
    service: AutomationService = Depends(get_service),
) -> None:
    """Ordnet einen Feuchtesensor dem Standort zu; evaluate liest dann seine Werte."""
    try:
        service.link_sensor(location_id, device_id)
    except (LocationNotFoundError, DeviceNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SensorLinkError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
