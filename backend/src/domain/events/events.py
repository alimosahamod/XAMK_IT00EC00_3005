from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

# Domain Events (Phase 11, Observer): unveraenderliche Nachrichten "das ist passiert".
# Reine Dataclasses - kein ORM, kein HTTP. Der EventBus waehlt die Subscriber
# ueber die Klasse des Events; `event_type` ist der fachliche Name, der z.B.
# in alerts.event_type landet (und in Phase 12 ueber den WebSocket geht).
#
# location_id und zone_id werden beim Publish vom Geraet kopiert. Ist das
# Geraet nicht zugewiesen, bleiben beide None - es wird nichts erfunden.


@dataclass(frozen=True)
class ReadingCreated:
    """Ein Messwert wurde gespeichert (nur bei tracking_enabled=true veroeffentlicht)."""

    event_type: ClassVar[str] = "reading.created"

    device_id: UUID
    value: float
    unit: str  # z.B. "vwc" oder "lux"
    source: str  # "simulation" oder "vendor"
    recorded_at: datetime
    location_id: UUID | None
    zone_id: UUID | None


@dataclass(frozen=True)
class ThresholdCrossed:
    """Feuchte liegt strikt unter dem unteren Schwellwert der Zone."""

    event_type: ClassVar[str] = "threshold.crossed"

    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    moisture: float
    threshold_low: float


@dataclass(frozen=True)
class CommandFailed:
    """Ein Befehl ist beim Ausfuehren fehlgeschlagen (Status "failed")."""

    event_type: ClassVar[str] = "command.failed"

    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    command_type: str
    message: str  # Fehlertext, z.B. "Max run time exceeded"


@dataclass(frozen=True)
class ActuatorStateChanged:
    """Ein Aktuator-Zustand wurde erfolgreich gespeichert."""

    event_type: ClassVar[str] = "state.changed"

    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    state: str  # neuer Zustand, z.B. "running" oder "error"
