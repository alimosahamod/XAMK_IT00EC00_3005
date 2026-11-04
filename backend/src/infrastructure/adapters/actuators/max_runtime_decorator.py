from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID

from domain.actuators.errors import PolicyViolationError
from domain.actuators.ports import ActuatorDecorator, ActuatorPort
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository


class MaxRunTimeActuatorDecorator(ActuatorDecorator):
    """Sicherheits-Policy: blockiert apply(), wenn der Aktuator zu lange `running` ist.

    "Seit wann running" kommt aus `actuator_states.updated_at` (Phase 8).
    Die Uhr (`now`) ist injizierbar, damit Tests die Zeit festlegen koennen.
    """

    policy_name = "maxRunTime"

    def __init__(
        self,
        inner: ActuatorPort,
        states: ActuatorStateRepository,
        max_run_time: timedelta,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        super().__init__(inner)
        self._states = states
        self._max_run_time = max_run_time
        self._now = now

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        running_since = self._states.get_running_since(device_id)
        if running_since is not None and self._now() - running_since > self._max_run_time:
            # Blockiert: inner wird NICHT aufgerufen.
            raise PolicyViolationError(self.policy_name, "Max run time exceeded")
        self._inner.apply(device_id, command, payload)
