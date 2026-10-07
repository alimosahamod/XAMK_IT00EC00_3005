import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    device_family: Mapped[str] = mapped_column(
    String(32),
    nullable=False,
    server_default=text("'simulation'"),
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

    # Phase 4: optionale Zuordnung zu einem Standort. Nullable, weil die
    # Geraete aus Phase 2/3 noch keinen Standort haben und trotzdem gueltig sind.
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    """
    __table_args__ = (backend/alembic/versions/abc123_device_family.py
    Index("ix_devices_role", "role"),
    Index("ix_devices_family", "device_family"),
    )
    """

    __table_args__ = (
    Index("ix_devices_role", "role"),
    Index("ix_devices_family", "device_family"),
    )
    # (Name kann auch der NAMING_CONVENTION aus base.py ueberlassen werden.)


class LocationRow(Base):
    """ORM-Zeile fuer einen Standort in der `locations`-Tabelle (Phase 4)."""

    __tablename__ = "locations"

    # Gleiche Konvention wie bei DeviceRow: die DB vergibt die UUID.
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # Eine Location besitzt ihre Zonen. Loeschen der Location loescht die Zonen,
    # damit keine Zone ohne Standort zurueckbleibt.
    zones: Mapped[list["ZoneRow"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ZoneRow(Base):
    """ORM-Zeile fuer eine Zone; gehoert zu genau einer Location."""

    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Die Namenskonvention der Aufgabe: location_id, nie greenhouse_id.
    location_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Numeric statt Float: die Schwellwerte sind fachliche Grenzen und sollen
    # nicht durch Binaerrundung verrutschen. Die Domain rechnet mit float.
    moisture_threshold_low: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    moisture_threshold_high: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    # Der Zeitplan ist pro Zone frei aufgebaut, deshalb JSONB statt fester Spalten.
    schedule: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    location: Mapped["LocationRow"] = relationship(back_populates="zones")

    __table_args__ = (
        # Zonen werden immer ueber ihre Location gelesen.
        Index("ix_zones_location_id", "location_id"),
    )


class ReadingRow(Base):
    """ORM-Zeile fuer einen gespeicherten Messwert (Phase 5).

    Jeder Lesevorgang fuegt eine neue Zeile ein. So entsteht eine Historie,
    die spaeter Strategy (Phase 6) und Diagramme nutzen.
    """

    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Messwerte gehoeren zu ihrem Geraet; wird es geloescht, verschwinden sie mit.
    device_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )

    # asdecimal=False: die Domain rechnet mit float, nicht mit Decimal.
    value: Mapped[float] = mapped_column(Numeric(12, 4, asdecimal=False), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    # Der Zeitpunkt kommt vom Adapter (Messzeit), nicht vom Insert.
    recorded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class AutomationRuleRow(Base):
    """ORM-Zeile fuer die aktive Automatisierungs-Strategie eines Standorts (Phase 6).

    Eigene Tabelle statt Spalten auf `locations`: die Automatisierung ist ein
    eigenes Thema, LocationRow bleibt so wie in Phase 4.
    """

    __tablename__ = "automation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # unique=True: hoechstens eine aktive Strategie pro Standort. Wird der
    # Standort geloescht, ist seine Regel bedeutungslos -> CASCADE.
    location_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # "conservative" | "aggressive". Gueltige Keys prueft der Code
    # (get_strategy), nicht die DB - eine dritte Strategie braucht so
    # keine Migration.
    strategy_key: Mapped[str] = mapped_column(String(32), nullable=False)

    # Optionale Feineinstellungen der Strategie, deshalb frei als JSONB.
    parameters: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Bei jedem Update neu gesetzt, damit sichtbar ist, wann umgestellt wurde.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# Index fuer "neuester Wert pro Geraet": erst nach device_id filtern,
# dann absteigend nach Zeit - die oberste Zeile ist der aktuelle Wert.
Index(
    "ix_sensor_readings_device_id_recorded_at",
    ReadingRow.device_id,
    ReadingRow.recorded_at.desc(),
)
