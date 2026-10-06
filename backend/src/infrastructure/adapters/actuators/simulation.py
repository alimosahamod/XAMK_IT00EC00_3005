import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from domain.actuators.ports import ActuatorPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppliedCommand:
    device_id: UUID
    command: str
    payload: dict = field(default_factory=dict)
    applied_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SimulationActuatorAdapter(ActuatorPort):
    """Innerster Aktuator-Adapter: merkt sich Befehle und loggt sie.

    Kein GPIO, keine echte Hardware. Phase 9 wickelt Decorators um diese Klasse.
    """

    def __init__(self):
        self.applied: list[AppliedCommand] = []

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        entry = AppliedCommand(device_id=device_id, command=command, payload=dict(payload))
        self.applied.append(entry)
        logger.info("Simulated actuator %s: %s %s", device_id, command, payload)
