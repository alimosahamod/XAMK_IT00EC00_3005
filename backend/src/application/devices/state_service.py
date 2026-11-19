from uuid import UUID

from domain.actuators.context import ActuatorContext
from domain.actuators.state import INITIAL_STATE
from domain.devices.entity import Device
from domain.devices.errors import DeviceNotFoundError
from domain.events.bus import EventBus
from domain.events.events import ActuatorStateChanged
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.device_repository import DeviceRepository


class ActuatorStateService:
    """Laedt den Zustand, laesst den Context den Wechsel pruefen, speichert ihn.

    Phase 10 (Command) ruft spaeter genau diesen Ablauf auf.
    Phase 11: publiziert nach jedem gespeicherten Wechsel `state.changed`.
    """

    def __init__(self, devices: DeviceRepository, states: ActuatorStateRepository, bus: EventBus):
        self._devices = devices
        self._states = states
        self._bus = bus

    def transition(self, device_id: UUID, target: str) -> Device:
        # 1. Nur echte Aktuatoren haben einen Zustand -> sonst 404.
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(f"No actuator with id {device_id}")

        # 2. Gespeicherten Zustand laden und in den Context geben.
        context = ActuatorContext(self._states.get_state(device_id) or INITIAL_STATE)

        # 3. Der Context prueft den Wechsel. Ist er illegal, wirft er
        #    IllegalTransitionError und Schritt 4 wird nie erreicht.
        context.transition(target)

        # 4. Nur ein erlaubter Wechsel landet in der Datenbank.
        self._states.save_state(device_id, context.state)

        # 5. Phase 11: nach dem erfolgreichen Speichern publizieren. Ob daraus ein
        #    Alarm wird (nur bei "error"), entscheidet der Subscriber, nicht dieser Service.
        self._bus.publish(
            ActuatorStateChanged(
                device_id=device_id,
                location_id=device.location_id,
                zone_id=device.zone_id,
                state=context.state,
            )
        )
        return self._devices.get_device(device_id)
