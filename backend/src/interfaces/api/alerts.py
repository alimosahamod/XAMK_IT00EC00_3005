from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from application.alerts.dto import AlertDto
from infrastructure.db import get_db
from infrastructure.persistence.alert_repository import AlertRepository

# Phase 11: nur LESEN. Alarme entstehen ausschliesslich ueber den EventBus
# (AlertPersistenceSubscriber). Resolve (PATCH) kommt erst in Phase 13.
router = APIRouter(prefix="/api/alerts", tags=["alerts"])

ALLOWED_STATUS = ("active", "resolved", "all")


def get_repository(db: Session = Depends(get_db)) -> AlertRepository:
    return AlertRepository(db)


@router.get(
    "",
    response_model=list[AlertDto],
    responses={400: {"description": "status is not active, resolved or all"}},
)
def list_alerts(
    status_filter: str = Query(default="active", alias="status", description="active | resolved | all"),
    location_id: UUID | None = Query(default=None, description="Only alerts of this location"),
    zone_id: UUID | None = Query(default=None, description="Only alerts of this zone"),
    since: datetime | None = Query(default=None, description="Only alerts with created_at >= since"),
    limit: int = Query(default=50, ge=1, le=200, description="Max number of rows, newest first"),
    alerts: AlertRepository = Depends(get_repository),
) -> list[AlertDto]:
    """Event-Feed: gespeicherte Alarme, neueste zuerst (das Dashboard pollt alle 5 s)."""
    if status_filter not in ALLOWED_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status must be one of {', '.join(ALLOWED_STATUS)}",
        )
    rows = alerts.list_alerts(
        status=None if status_filter == "all" else status_filter,
        location_id=location_id,
        zone_id=zone_id,
        since=since,
        limit=limit,
    )
    return [AlertDto.model_validate(row) for row in rows]
