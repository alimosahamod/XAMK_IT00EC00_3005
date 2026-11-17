from uuid import UUID

from domain.actuators.context import ActuatorContext
from domain.actuators.ports import ActuatorPort
from domain.commands.base import ActuatorCommand, ActuatorStateStore
from domain.commands.errors import InvalidCommandError


class SetLightLevelCommand(ActuatorCommand):
    """Setzt die Helligkeit (0-100). Payload: {"level": 70}.

    Aus `idle` schaltet der Befehl das Licht ein (-> running).
    Laeuft das Licht schon, aendert er nur die Helligkeit; der Zustand bleibt running.
    """

    command_type = "set_light_level"
    port_command = "set_level"
    state_command = "start"
    target_state = "running"

    def __init__(self, device_id: UUID, payload: dict, port: ActuatorPort, states: ActuatorStateStore):
        # Payload frueh pruefen: ein kaputter Befehl wird gar nicht erst gebaut.
        level = payload.get("level")
        if not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= 100:
            raise InvalidCommandError("set_light_level needs payload.level as integer 0-100")
        super().__init__(device_id, payload, port, states)

    def is_allowed(self, context: ActuatorContext) -> bool:
        # Zusaetzlich zu "start" (aus idle) auch erlaubt, wenn das Licht schon laeuft.
        return context.state == "running" or super().is_allowed(context)


class SwitchOffLightCommand(ActuatorCommand):
    # running -> idle; Gegenstueck zu set_light_level. Nur eine neue Klasse + ein Registry-Eintrag.
    command_type = "switch_off_light"
    port_command = "off"
    state_command = "stop"
    target_state = "idle"
