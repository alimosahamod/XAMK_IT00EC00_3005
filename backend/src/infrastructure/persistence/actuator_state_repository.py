from uuid import UUID

from sqlalchemy.orm import Session

from infrastructure.persistence.models import ActuatorStateRow


class ActuatorStateRepository:
    """Liest und speichert den Zustand eines Aktuators in `actuator_states`.

    Kennt keine Regeln: ob ein Wechsel erlaubt ist, entscheidet vorher der
    ActuatorContext. Hier wird nur gespeichert, was schon geprueft wurde.
    """

    def __init__(self, db: Session):
        self._db = db

    def get_state(self, device_id: UUID) -> str | None:
        row = self._db.get(ActuatorStateRow, device_id)
        return None if row is None else row.state

    def save_state(self, device_id: UUID, state: str) -> None:
        row = self._db.get(ActuatorStateRow, device_id)
        if row is None:
            # Fallback, falls ein Aktuator noch keine Zeile hat.
            self._db.add(ActuatorStateRow(device_id=device_id, state=state))
        else:
            row.state = state  # updated_at setzt onupdate automatisch
        self._db.commit()
