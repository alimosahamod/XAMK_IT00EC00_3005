from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from application.overview.dto import LocationOverviewDto
from application.overview.facade import LocationOverviewFacade
from domain.automation.errors import LocationNotFoundError
from infrastructure.db import get_db

router = APIRouter(tags=["overview"])


def get_facade(db: Session = Depends(get_db)) -> LocationOverviewFacade:
    # Der Router kennt nur die Facade - keine Repositories, keinen AutomationService.
    return LocationOverviewFacade.from_session(db)


@router.get(
    "/api/locations/{location_id}/overview",
    response_model=LocationOverviewDto,
    responses={404: {"description": "Location not found"}},
)
def get_overview(
    location_id: UUID,
    facade: LocationOverviewFacade = Depends(get_facade),
) -> LocationOverviewDto:
    """Snapshot des Standorts: Geraete, neueste Messwerte, Strategie und Empfehlung."""
    try:
        return facade.get_overview(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
