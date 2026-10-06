from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.sensors.reading import Reading
from infrastructure.persistence.models import ReadingRow


class ReadingRepository:
    """Speichert Messwerte und liest die neuesten pro Geraet."""

    def __init__(self, db: Session):
        self._db = db

    def insert(self, reading: Reading) -> Reading:
        # Immer INSERT, nie UPDATE: jede Messung bleibt in der Historie.
        row = ReadingRow(
            device_id=reading.device_id,
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return self._to_reading(row)

    def list_for_device(self, device_id: UUID, limit: int = 20) -> list[Reading]:
        # Nutzt den Index (device_id, recorded_at DESC): neueste zuerst.
        stmt = (
            select(ReadingRow)
            .where(ReadingRow.device_id == device_id)
            .order_by(ReadingRow.recorded_at.desc())
            .limit(limit)
        )
        rows = self._db.execute(stmt).scalars().all()
        return [self._to_reading(row) for row in rows]

    @staticmethod
    def _to_reading(row: ReadingRow) -> Reading:
        return Reading(
            device_id=row.device_id,
            value=float(row.value),
            unit=row.unit,
            source=row.source,
            recorded_at=row.recorded_at,
        )
