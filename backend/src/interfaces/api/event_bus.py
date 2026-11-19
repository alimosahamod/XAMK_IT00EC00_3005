from fastapi import Depends
from sqlalchemy.orm import Session

from application.alerts.subscribers import (
    AlertPersistenceSubscriber,
    MoistureThresholdSubscriber,
)
from domain.events.bus import EventBus
from domain.events.events import (
    ActuatorStateChanged,
    CommandFailed,
    ReadingCreated,
    ThresholdCrossed,
)
from infrastructure.db import get_db
from infrastructure.persistence.alert_repository import AlertRepository
from infrastructure.persistence.location_repository import LocationRepository

# Composition Root fuer den Observer (Phase 11): nur HIER wird festgelegt,
# wer auf welches Event hoert. Publisher bekommen den fertigen Bus injiziert.


def build_event_bus(db: Session) -> EventBus:
    """Baut einen Bus und meldet beide Subscriber an (Reihenfolge = Aufruf-Reihenfolge)."""
    bus = EventBus()
    threshold = MoistureThresholdSubscriber(bus, LocationRepository(db))
    persistence = AlertPersistenceSubscriber(AlertRepository(db))

    bus.subscribe(ReadingCreated, threshold.on_reading)
    bus.subscribe(ThresholdCrossed, persistence.on_threshold)
    bus.subscribe(CommandFailed, persistence.on_command)
    bus.subscribe(ActuatorStateChanged, persistence.on_state)
    return bus


def get_event_bus(db: Session = Depends(get_db)) -> EventBus:
    # FastAPI cached Dependencies pro Request: alle Services eines Requests
    # bekommen denselben Bus mit derselben DB-Session.
    return build_event_bus(db)
