from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from infrastructure.persistence.models import ActuatorExecutionLogRow


class ExecutionLogRepository:
    """Schreibt und liest Ausfuehrungsversuche in `actuator_execution_log`."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, device_id: UUID, success: bool, policy_applied: list[str], message: str | None) -> None:
        self._db.add(
            ActuatorExecutionLogRow(
                device_id=device_id,
                success=success,
                policy_applied=policy_applied,
                message=message,
            )
        )
        self._db.commit()

    def list_recent(self, limit: int = 20) -> list[ActuatorExecutionLogRow]:
        # Neueste Versuche zuerst - so zeigt das Dashboard das Log an.
        query = (
            select(ActuatorExecutionLogRow)
            .order_by(ActuatorExecutionLogRow.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(query))
