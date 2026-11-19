from uuid import UUID

from sqlalchemy.orm import Session

from infrastructure.persistence.models import AlertRow


class AlertRepository:
    """Schreibt Alarme in `alerts`.

    Einziger Aufrufer ist der AlertPersistenceSubscriber. Publisher (Ingest,
    CommandService, Zustandswechsel) importieren diese Klasse nie.
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
