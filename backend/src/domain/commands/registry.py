from uuid import UUID

from domain.actuators.ports import ActuatorPort
from domain.commands.base import ActuatorCommand, ActuatorStateStore
from domain.commands.errors import InvalidCommandError
from domain.commands.light import SetLightLevelCommand, SwitchOffLightCommand
from domain.commands.pump import StartPumpCommand, StopPumpCommand

# Registry: command_type -> Klasse. Ein neuer Befehl = neue Klasse + ein Eintrag hier,
# statt einer if/elif-Kette ueber alle Befehlsnamen.
COMMANDS: dict[str, type[ActuatorCommand]] = {
    cls.command_type: cls
    for cls in (StartPumpCommand, StopPumpCommand, SetLightLevelCommand, SwitchOffLightCommand)
}


def create_command(
    command_type: str, device_id: UUID, payload: dict, port: ActuatorPort, states: ActuatorStateStore
) -> ActuatorCommand:
    """Baut das passende Command-Objekt. Unbekannter Typ -> InvalidCommandError."""
    try:
        command_class = COMMANDS[command_type]
    except KeyError:
        raise InvalidCommandError(
            f"Unknown command_type {command_type!r}. Known: {', '.join(COMMANDS)}"
        )
    return command_class(device_id, payload, port, states)
