from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from infrastructure.persistence.models import AutomationRuleRow


class AutomationRuleRepository:
    """Speichert und liest die aktive Strategie pro Standort."""

    def __init__(self, db: Session):
        self._db = db

    def get_strategy_key(self, location_id: UUID) -> str | None:
        """Liefert den gespeicherten Key, oder None wenn noch keine Regel existiert."""
        stmt = select(AutomationRuleRow.strategy_key).where(
            AutomationRuleRow.location_id == location_id
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_rule(self, location_id: UUID) -> tuple[str, dict] | None:
        """Liefert Key und Parameter, oder None wenn noch keine Regel existiert.

        Nur Spalten statt der ganzen ORM-Zeile: der Service baut daraus den
        Kontext, die Strategie bekommt nie eine AutomationRuleRow.
        """
        stmt = select(AutomationRuleRow.strategy_key, AutomationRuleRow.parameters).where(
            AutomationRuleRow.location_id == location_id
        )
        row = self._db.execute(stmt).one_or_none()
        if row is None:
            return None
        return row.strategy_key, row.parameters

    def upsert(
        self, location_id: UUID, strategy_key: str, parameters: dict | None = None
    ) -> str:
        """Legt die Regel an oder ueberschreibt die bestehende.

        INSERT ... ON CONFLICT (location_id) DO UPDATE ist atomar: auch zwei
        gleichzeitige Requests erzeugen keine zweite Zeile und keinen
        UNIQUE-Fehler. onupdate greift bei Core-Upserts nicht, deshalb wird
        updated_at hier explizit gesetzt.
        """
        values = {
            "location_id": location_id,
            "strategy_key": strategy_key,
            "parameters": parameters or {},
        }
        stmt = insert(AutomationRuleRow).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[AutomationRuleRow.location_id],
            set_={
                "strategy_key": stmt.excluded.strategy_key,
                "parameters": stmt.excluded.parameters,
                "updated_at": func.now(),
            },
        ).returning(AutomationRuleRow.strategy_key)

        try:
            saved_key = self._db.execute(stmt).scalar_one()
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return saved_key
