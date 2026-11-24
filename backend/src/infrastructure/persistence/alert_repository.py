from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from infrastructure.persistence.models import AlertRow


class AlertRepository:
    """Schreibt und liest Alarme in `alerts`.

    Geschrieben wird nur vom AlertPersistenceSubscriber, gelesen vom Alerts-Router.
    Publisher (Ingest, CommandService, Zustandswechsel) importieren diese Klasse nie.
    """

    def __init__(self, db: Session):
        self._db = db

    def add(
        self,
        *,
        event_type: str,
        severity: str,
        message: str,
        device_id: UUID | None,
        location_id: UUID | None,
        zone_id: UUID | None,
    ) -> AlertRow:
        row = AlertRow(
            event_type=event_type,
            severity=severity,
            message=message,
            device_id=device_id,
            location_id=location_id,
            zone_id=zone_id,
            status="active",
        )
        self._db.add(row)
        try:
            self._db.commit()
        except Exception:
            # Session wieder benutzbar machen, dann Fehler weitergeben.
            self._db.rollback()
            raise
        self._db.refresh(row)
        return row

    def list_alerts(
        self,
        *,
        status: str | None,
        location_id: UUID | None,
        zone_id: UUID | None,
        since: datetime | None,
        limit: int,
    ) -> list[AlertRow]:
        """Fuer GET /api/alerts: neueste zuerst. Ein Filter mit None wird ignoriert."""
        query = select(AlertRow)
        if status is not None:  # None = "all"
            query = query.where(AlertRow.status == status)
        if location_id is not None:
            query = query.where(AlertRow.location_id == location_id)
        if zone_id is not None:
            query = query.where(AlertRow.zone_id == zone_id)
        if since is not None:
            query = query.where(AlertRow.created_at >= since)
        query = query.order_by(AlertRow.created_at.desc()).limit(limit)
        return list(self._db.scalars(query))
