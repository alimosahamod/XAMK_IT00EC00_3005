from domain.events.bus import EventBus
from domain.events.events import (
    ActuatorStateChanged,
    CommandFailed,
    ReadingCreated,
    ThresholdCrossed,
)
from infrastructure.persistence.alert_repository import AlertRepository
from infrastructure.persistence.location_repository import LocationRepository

# Observer (Phase 11): die Subscriber reagieren selbst auf Events.
# Die Publisher wissen nicht, dass es sie gibt.


class MoistureThresholdSubscriber:
    """Prueft jeden ReadingCreated und meldet zu trockene Zonen als ThresholdCrossed.

    Regel: unit == "vwc", zone_id gesetzt und value STRIKT unter
    moisture_threshold_low der Zone. Ohne Zone passiert nichts.
    Er schreibt selbst keinen Alarm, sondern publiziert nur ein neues Event.
    """

    def __init__(self, bus: EventBus, locations: LocationRepository):
        self._bus = bus
        self._locations = locations

    def on_reading(self, event: ReadingCreated) -> None:
        if event.unit != "vwc" or event.zone_id is None:
            return
        low = self._locations.get_zone_threshold_low(event.zone_id)
        if low is None or not event.value < low:
            return
        self._bus.publish(
            ThresholdCrossed(
                device_id=event.device_id,
                location_id=event.location_id,
                zone_id=event.zone_id,
                moisture=event.value,
                threshold_low=low,
            )
        )


class AlertPersistenceSubscriber:
    """Schreibt pro passendem Event genau eine aktive Zeile in `alerts`.

    Einzige Stelle, die AlertRepository benutzt. location_id und zone_id
    kommen 1:1 aus dem Event (also vom Geraet, oder None).
    """

    def __init__(self, alerts: AlertRepository):
        self._alerts = alerts

    def on_threshold(self, event: ThresholdCrossed) -> None:
        self._insert(event, "warning", "Moisture below zone low")

    def on_command(self, event: CommandFailed) -> None:
        # Nachricht = Fehlertext des Befehls, z.B. "Max run time exceeded".
        self._insert(event, "warning", event.message)

    def on_state(self, event: ActuatorStateChanged) -> None:
        # Nur der Wechsel nach "error" ist ein Alarm; running/idle usw. nicht.
        if event.state != "error":
            return
        self._insert(event, "critical", "Actuator entered error")

    def _insert(self, event: ThresholdCrossed | CommandFailed | ActuatorStateChanged, severity: str, message: str) -> None:
        self._alerts.add(
            event_type=event.event_type,
            severity=severity,
            message=message,
            device_id=event.device_id,
            location_id=event.location_id,
            zone_id=event.zone_id,
        )
