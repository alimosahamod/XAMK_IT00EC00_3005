from uuid import UUID

from sqlalchemy.orm import Session

from application.actuators.actuator_chain import build_actuator
from application.commands.dto import CommandLogDto, CommandResultDto
from application.commands.mappers import command_logs_to_dtos
from domain.actuators.ports import ActuatorPort
from domain.commands.invoker import CommandInvoker
from domain.commands.registry import create_command
from domain.devices.entity import Device
from domain.devices.errors import DeviceNotFoundError
from domain.events.bus import EventBus
from domain.events.events import ActuatorStateChanged, CommandFailed
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.command_log_repository import CommandLogRepository
from infrastructure.persistence.device_repository import DeviceRepository


class CommandService:
    """Client im Command Pattern: baut das Command-Objekt und gibt es dem Invoker.

    Verdrahtet State-Guard (ActuatorStateRepository), dekorierten Port
    (build_actuator aus Phase 9) und command_log. Selbst fuehrt er nichts aus.
    Phase 11: publiziert danach `command.failed` bzw. `state.changed` auf dem Bus.
    """

    def __init__(
        self,
        devices: DeviceRepository,
        states: ActuatorStateRepository,
        port: ActuatorPort,
        invoker: CommandInvoker,
        log: CommandLogRepository,
        bus: EventBus,
    ):
        self._devices = devices
        self._states = states
        self._port = port
        self._invoker = invoker
        self._log = log
        self._bus = bus

    @classmethod
    def from_session(cls, db: Session, bus: EventBus) -> "CommandService":
        log = CommandLogRepository(db)
        return cls(
            DeviceRepository(db),
            ActuatorStateRepository(db),
            build_actuator(db),
            CommandInvoker(log),
            log,
            bus,
        )

    def submit(self, command_type: str, device_id: UUID, payload: dict | None = None) -> CommandResultDto:
        # Nur echte Aktuatoren duerfen Befehle bekommen. Ohne Geraet gibt es auch
        # keine Log-Zeile (device_id ist ein FK auf devices).
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(f"No actuator with id {device_id}")

        # Registry statt if/elif; unbekannter Typ -> InvalidCommandError.
        command = create_command(command_type, device_id, payload or {}, self._port, self._states)
        state_before = self._states.get_state(device_id)
        result = self._invoker.submit(command)
        self._publish_outcome(device, result.status, result.error_message, command.command_type, state_before)
        return CommandResultDto(
            command_type=command.command_type,
            device_id=command.device_id,
            payload=command.payload,
            status=result.status,
            error_message=result.error_message,
        )

    def _publish_outcome(
        self, device: Device, status: str, error_message: str | None, command_type: str, state_before: str | None
    ) -> None:
        # location_id/zone_id vom Geraet; beim nicht zugewiesenen Seed-Pump beide None.
        if status == "failed":
            # z.B. MaxRunTime-Decorator blockiert stop_pump -> "Max run time exceeded".
            # "rejected" (Guard) ist kein Ausfuehrungsfehler und erzeugt kein Event.
            self._bus.publish(
                CommandFailed(
                    device_id=device.id,
                    location_id=device.location_id,
                    zone_id=device.zone_id,
                    command_type=command_type,
                    message=error_message or "Command failed",
                )
            )
        elif status == "success":
            # Der Command hat den Zustand nur gespeichert, wenn er sich geaendert hat.
            state_after = self._states.get_state(device.id)
            if state_after != state_before:
                self._bus.publish(
                    ActuatorStateChanged(
                        device_id=device.id,
                        location_id=device.location_id,
                        zone_id=device.zone_id,
                        state=state_after,
                    )
                )

    def list_commands(self, limit: int) -> list[CommandLogDto]:
        return command_logs_to_dtos(self._log.list_recent(limit))
