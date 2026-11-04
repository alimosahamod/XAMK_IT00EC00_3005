from uuid import UUID

from domain.actuators.ports import ActuatorDecorator, ActuatorPort
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository


class LoggingActuatorDecorator(ActuatorDecorator):
    """Aeusserste Schicht: schreibt fuer JEDEN Versuch eine Zeile ins Execution-Log."""

    policy_name = "logging"

    def __init__(self, inner: ActuatorPort, log_repo: ExecutionLogRepository):
        super().__init__(inner)
        self._log = log_repo

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        try:
            self._inner.apply(device_id, command, payload)
        except Exception as exc:
            # Fehlschlag (z.B. Policy blockiert): trotzdem loggen, dann weiterwerfen.
            self._log.add(device_id, False, self.policies(), str(exc))
            raise
        # Erfolg: ebenfalls loggen.
        self._log.add(device_id, True, self.policies(), None)
