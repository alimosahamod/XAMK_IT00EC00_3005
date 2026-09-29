from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.locations.entity import LocationConfig
from infrastructure.persistence.models import LocationRow, ZoneRow


class LocationRepository:
    """Speichert und liest Standort-Konfigurationen."""

    def __init__(self, db: Session):
        self._db = db

    def save_config(self, config: LocationConfig) -> tuple[LocationRow, list[ZoneRow]]:
        """Schreibt Standort und Zonen in genau einer Transaktion.

        Der Commit steht erst am Ende. Schlaegt eine Zone fehl, macht das
        Rollback auch den Standort rueckgaengig: es gibt keinen Standort
        ohne seine Zonen in der Datenbank.
        """
        location_row = LocationRow(name=config.location.name)
        self._db.add(location_row)

        try:
            # flush schickt das INSERT, holt die von der DB erzeugte id,
            # committet aber noch nicht.
            self._db.flush()

            zone_rows = [
                ZoneRow(
                    location_id=location_row.id,
                    name=zone.name,
                    moisture_threshold_low=zone.moisture_threshold_low,
                    moisture_threshold_high=zone.moisture_threshold_high,
                    schedule=zone.schedule,
                )
                for zone in config.location.zones
            ]
            self._db.add_all(zone_rows)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        self._db.refresh(location_row)
        for row in zone_rows:
            self._db.refresh(row)
        return location_row, zone_rows

    def get_config(self, location_id: UUID) -> tuple[LocationRow, list[ZoneRow]] | None:
        """Liefert Standort und Zonen, oder None wenn es den Standort nicht gibt."""
        location_row = self._db.get(LocationRow, location_id)
        if location_row is None:
            return None

        stmt = (
            select(ZoneRow)
            .where(ZoneRow.location_id == location_id)
            .order_by(ZoneRow.name)
        )
        zone_rows = list(self._db.execute(stmt).scalars().all())
        return location_row, zone_rows
