from uuid import UUID

from sqlalchemy.orm import Session

from application.actuators.actuator_chain import build_actuator
from application.commands.dto import CommandLogDto, CommandResultDto
from application.commands.mappers import command_logs_to_dtos
from domain.actuators.ports import ActuatorPort
from domain.commands.invoker import CommandInvoker
from domain.commands.registry import create_command
from domain.devices.errors import DeviceNotFoundError
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.command_log_repository import CommandLogRepository
from infrastructure.persistence.device_repository import DeviceRepository


class CommandService:
    """Client im Command Pattern: baut das Command-Objekt und gibt es dem Invoker.

    Verdrahtet State-Guard (ActuatorStateRepository), dekorierten Port
    (build_actuator aus Phase 9) und command_log. Selbst fuehrt er nichts aus.
    """

    def __init__(
        self,
        devices: DeviceRepository,
        states: ActuatorStateRepository,
        port: ActuatorPort,
        invoker: CommandInvoker,
        log: CommandLogRepository,
    ):
        self._devices = devices
        self._states = states
        self._port = port
        self._invoker = invoker
        self._log = log

    @classmethod
    def from_session(cls, db: Session) -> "CommandService":
        log = CommandLogRepository(db)
        return cls(
            DeviceRepository(db),
            ActuatorStateRepository(db),
            build_actuator(db),
            CommandInvoker(log),
            log,
        )

    def submit(self, command_type: str, device_id: UUID, payload: dict | None = None) -> CommandResultDto:
        # Nur echte Aktuatoren duerfen Befehle bekommen. Ohne Geraet gibt es auch
        # keine Log-Zeile (device_id ist ein FK auf devices).
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(f"No actuator with id {device_id}")

        # Registry statt if/elif; unbekannter Typ -> InvalidCommandError.
        command = create_command(command_type, device_id, payload or {}, self._port, self._states)
        result = self._invoker.submit(command)
        return CommandResultDto(
            command_type=command.command_type,
            device_id=command.device_id,
            payload=command.payload,
            status=result.status,
            error_message=result.error_message,
        )

    def list_commands(self, limit: int) -> list[CommandLogDto]:
        return command_logs_to_dtos(self._log.list_recent(limit))
