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
