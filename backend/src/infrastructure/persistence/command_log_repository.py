from uuid import UUID

from sqlalchemy.orm import Session

from infrastructure.persistence.models import CommandLogRow


class CommandLogRepository:
    """Schreibt Befehlsversuche in `command_log` (Phase 10)."""

    def __init__(self, db: Session):
        self._db = db

    def add(
        self, command_type: str, device_id: UUID, payload: dict, status: str, error_message: str | None
    ) -> None:
        self._db.add(
            CommandLogRow(
                command_type=command_type,
                device_id=device_id,
                payload=payload,
                status=status,
                error_message=error_message,
            )
        )
        self._db.commit()
