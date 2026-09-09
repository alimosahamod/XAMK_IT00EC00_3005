import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, String, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.sql import func

from infrastructure.persistence.base import Base


class DeviceRow(Base):
    """ORM-Zeile fuer Sensoren (und spaeter Aktoren) in der `devices`-Tabelle."""

    __tablename__ = "devices"

    # Identifier: UUID Primary Key.
    # Spaltentyp Postgres-UUID setzen, primary_key=True, und den Default
    # server-seitig erzeugen (gen_random_uuid()), nicht in Python -
    # siehe Begruendung aus Step 2 (DB garantiert Eindeutigkeit).
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # device_type: fachlicher Sensortyp, z.B. "moisture_sensor", "light_sensor".
    #String(64), nullable=False.
    device_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )

    # role: in dieser Phase immer "sensor". Eigene Spalte statt Hartkodierung,
    # damit Phase 3 dieselbe Tabelle mit role="actuator" nutzen kann.
    #String(32), nullable=False, sinnvoller Default "sensor".
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'sensor'")
    )

    # display_name: optionales Label vom Nutzer/Creator.
    #String(128), nullable=True -> Mapped[str | None].
    display_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    # default_config: typ-spezifische Defaults vom jeweiligen Creator
    # (z.B. Schwellwert vs. Einheit) - deshalb JSON statt starrer Spalten.
    # JSONB, nullable=False, sinnvoller Default (leeres Objekt).
    default_config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # created_at: Server-seitiger Zeitstempel, damit er unabhaengig von
    # Client-Uhr/Zeitzone konsistent ist.
    # TIMESTAMP mit Zeitzone, server_default=func.now().
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_devices_role", "role"),)
    # (Name kann auch der NAMING_CONVENTION aus base.py ueberlassen werden.)
