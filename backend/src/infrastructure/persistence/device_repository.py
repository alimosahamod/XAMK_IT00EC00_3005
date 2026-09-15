from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.sensors.entity import Sensor
from infrastructure.persistence.models import DeviceRow


class DeviceRepository:
    """Speichert und liest Sensor-Zeilen; mappt zwischen Row und Domain-Sensor."""

    def __init__(self, db: Session):
        self._db = db

    def save_sensor(self, sensor: Sensor) -> Sensor:
        row = DeviceRow(
            device_type=sensor.device_type,
            role="sensor",
            display_name=sensor.display_name,
            default_config=sensor.default_config,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)  # holt die DB-generierte id
        return self._to_domain(row)

    def list_sensors(self) -> list[Sensor]:
        stmt = (
            select(DeviceRow)
            .where(DeviceRow.role == "sensor")
            .order_by(DeviceRow.created_at.desc())  # neueste zuerst
        )
        rows = self._db.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: DeviceRow) -> Sensor:
        return Sensor(
            id=row.id,
            device_type=row.device_type,
            display_name=row.display_name,
            default_config=row.default_config,
        )
