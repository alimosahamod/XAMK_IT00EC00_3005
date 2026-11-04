from abc import ABC, abstractmethod
from uuid import UUID


class ActuatorPort(ABC):
    """Target-Schnittstelle (Port) fuer alle Aktuatoren.

    Phase 5 liefert nur einen Simulations-Adapter. Phase 9 wickelt Decorators
    um diesen Port (z.B. Logging, Sicherheitspruefung), ohne ihn zu aendern.
    """

    @abstractmethod
    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        """Fuehrt einen Befehl aus, z.B. command="on" mit {"duration_s": 30}."""


class ActuatorDecorator(ActuatorPort):
    """Basis fuer alle Decorators: implementiert denselben Port und haelt den inneren.

    Ein Decorator fuegt Verhalten vor/nach dem Aufruf hinzu und reicht ihn
    dann an `inner` weiter. Der Aufrufer merkt nicht, wie viele Schichten es gibt.
    """

    policy_name: str = ""

    def __init__(self, inner: ActuatorPort):
        self._inner = inner

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        self._inner.apply(device_id, command, payload)

    def policies(self) -> list[str]:
        # Sammelt die Policy-Namen von innen nach aussen, z.B. ["maxRunTime", "logging"].
        inner = self._inner.policies() if isinstance(self._inner, ActuatorDecorator) else []
        return inner + [self.policy_name]
