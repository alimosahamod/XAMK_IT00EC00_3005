from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Protocol
from uuid import UUID

from domain.actuators.context import ActuatorContext
from domain.actuators.ports import ActuatorPort
from domain.actuators.state import INITIAL_STATE
from domain.commands.errors import CommandRejectedError


@dataclass(frozen=True)
class CommandResult:
    """Ergebnis eines Befehls: "success" | "failed" | "rejected"."""

    status: str
    error_message: str | None = None


class Command(ABC):
    """Command-Interface: ein Request als Objekt.

    Das Objekt kennt alles, was es zum Ausfuehren braucht (Geraet, Payload,
    Empfaenger). Der Invoker ruft nur `execute()` auf und muss nicht wissen,
    was konkret passiert.
    """

    command_type: ClassVar[str]  # z.B. "start_pump" - so steht er in command_log

    def __init__(self, device_id: UUID, payload: dict):
        self.device_id = device_id
        self.payload = payload

    @abstractmethod
    def execute(self) -> None:
        """Fuehrt den Befehl aus. Wirft CommandRejectedError, wenn er nicht erlaubt ist."""


class ActuatorStateStore(Protocol):
    """Was ein Aktuator-Befehl vom Zustandsspeicher braucht (ActuatorStateRepository erfuellt das)."""

    def get_state(self, device_id: UUID) -> str | None: ...

    def save_state(self, device_id: UUID, state: str) -> None: ...


class ActuatorCommand(Command):
    """Gemeinsamer Ablauf aller Aktuator-Befehle: Guard -> Port -> Zustand.

    Receiver sind der (dekorierte) ActuatorPort und der Zustandsspeicher.
    Unterklassen setzen nur drei Klassenattribute - kein if/elif pro Befehl.
    """

    port_command: ClassVar[str]   # was der ActuatorPort bekommt, z.B. "on"
    state_command: ClassVar[str]  # Name in allowed_commands (Phase 8), z.B. "start"
    target_state: ClassVar[str]   # Zustand nach Erfolg, z.B. "running"

    def __init__(self, device_id: UUID, payload: dict, port: ActuatorPort, states: ActuatorStateStore):
        super().__init__(device_id, payload)
        self._port = port
        self._states = states

    def execute(self) -> None:
        context = ActuatorContext(self._states.get_state(self.device_id) or INITIAL_STATE)

        # 1. Guard: illegaler Befehl -> abbrechen, BEVOR Port oder Zustand angefasst werden.
        if not self.is_allowed(context):
            raise CommandRejectedError(self.command_type, context.state, context.allowed_commands())

        # 2. Port: laeuft durch den Decorator-Stapel aus Phase 9 (Logging, MaxRunTime).
        #    Wirft er (z.B. PolicyViolationError), wird Schritt 3 nie erreicht.
        self._port.apply(self.device_id, self.port_command, self.payload)

        # 3. Zustand: erst nach erfolgreichem apply wechseln und speichern.
        if context.state != self.target_state:
            context.transition(self.target_state)
            self._states.save_state(self.device_id, context.state)

    def is_allowed(self, context: ActuatorContext) -> bool:
        # Standard: die State-Maschine muss den passenden Befehl gerade anbieten.
        return self.state_command in context.allowed_commands()
