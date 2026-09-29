from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.devices.entity import Device
from domain.sensors.entity import Sensor
from infrastructure.persistence.models import DeviceRow

# Phase 2 Sensoren hatten noch keine Familie. Damit alte und neue Zeilen
# konsistent bleiben, bekommt der Sensor-Pfad diese Standardfamilie.
DEFAULT_FAMILY = "simulation"


class DeviceRepository:
    """Speichert und liest Geraete-Zeilen; mappt zwischen Row und Domain-Objekt."""

    def __init__(self, db: Session):
        self._db = db

    # --- Phase 2: Sensor-Pfad (bleibt erhalten) ---------------------------

    def save_sensor(self, sensor: Sensor) -> Sensor:
        row = DeviceRow(
            device_type=sensor.device_type,
            role="sensor",
            device_family=DEFAULT_FAMILY,
            display_name=sensor.display_name,
            default_config=sensor.default_config,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)  # holt die DB-generierte id
        return self._to_sensor(row)

    def list_sensors(self) -> list[Sensor]:
        stmt = (
            select(DeviceRow)
            .where(DeviceRow.role == "sensor")
            .order_by(DeviceRow.created_at.desc())  # neueste zuerst
        )
        rows = self._db.execute(stmt).scalars().all()
        return [self._to_sensor(row) for row in rows]

    # --- Phase 3: Geraete-Pfad (Sensoren und Aktuatoren) ------------------

    def save_device(self, device: Device) -> Device:
        row = self._to_row(device)
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return self._to_device(row)

    def save_devices(self, devices: list[Device]) -> list[Device]:
        # Ein Geraeteset gehoert zusammen, deshalb ein gemeinsamer Commit.
        rows = [self._to_row(device) for device in devices]
        self._db.add_all(rows)
        self._db.commit()
        for row in rows:
            self._db.refresh(row)
        return [self._to_device(row) for row in rows]

    def list_devices(
        self,
        *,
        device_family: str | None = None,
        role: str | None = None,
    ) -> list[Device]:
        stmt = select(DeviceRow)
        # Die Filter werden in SQL angewendet, nicht erst in Python.
        if device_family is not None:
            stmt = stmt.where(DeviceRow.device_family == device_family)
        if role is not None:
            stmt = stmt.where(DeviceRow.role == role)
        stmt = stmt.order_by(DeviceRow.created_at.desc())
        rows = self._db.execute(stmt).scalars().all()
        return [self._to_device(row) for row in rows]

    # --- Mapping ----------------------------------------------------------

    @staticmethod
    def _to_row(device: Device) -> DeviceRow:
        return DeviceRow(
            device_type=device.device_type,
            role=device.role,
            device_family=device.device_family,
            display_name=device.display_name,
            default_config=device.default_config,
        )

    @staticmethod
    def _to_device(row: DeviceRow) -> Device:
        return Device(
            id=row.id,
            device_type=row.device_type,
            role=row.role,
            device_family=row.device_family,
            # Die Spalte erlaubt NULL, das Domain-Device verlangt einen Namen.
            display_name=row.display_name or row.device_type,
            default_config=row.default_config,
        )

    @staticmethod
    def _to_sensor(row: DeviceRow) -> Sensor:
        return Sensor(
            id=row.id,
            device_type=row.device_type,
            display_name=row.display_name,
            default_config=row.default_config,
        )
