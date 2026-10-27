from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, aliased

from domain.sensors.reading import Reading
from infrastructure.persistence.models import DeviceRow, ReadingRow


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

    def latest_value_for_location(self, location_id: UUID, device_type: str) -> float | None:

        stmt = (
            select(ReadingRow.value)
            .join(DeviceRow, DeviceRow.id == ReadingRow.device_id)
            .where(DeviceRow.location_id == location_id, DeviceRow.device_type == device_type)
            .order_by(ReadingRow.recorded_at.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def latest_per_device_for_location(self, location_id: UUID) -> list[Reading]:
        #Neuester Messwert jedes Geraets am Standort, neueste zuerst (Phase 7).

        # Eine Abfrage fuer alle Geraete statt einer pro Geraet (kein N+1): 
        # DISTINCT ON (device_id) behaelt pro Geraet nur die erste Zeile nach recorded_at DESC - passt zum Index (device_id, recorded_at DESC).
        
        latest = (
            select(ReadingRow)
            .join(DeviceRow, DeviceRow.id == ReadingRow.device_id)
            .where(DeviceRow.location_id == location_id)
            .ext(distinct_on(ReadingRow.device_id))
            .order_by(ReadingRow.device_id, ReadingRow.recorded_at.desc())
        ).subquery()
        # DISTINCT ON erzwingt die Sortierung nach device_id; fuer die Anzeige
        # wird aussen noch einmal nach Zeit sortiert.
        newest = aliased(ReadingRow, latest)
        stmt = select(newest).order_by(newest.recorded_at.desc())
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
