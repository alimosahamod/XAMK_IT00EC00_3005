from sqlalchemy.orm import Session

from application.actuators.dto import ExecutionDto
from application.actuators.mappers import executions_to_dtos
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository


class ActuatorExecutionService:
    """Liest das Execution-Log des Decorator-Stapels (Phase 9).

    Ausgefuehrt wird seit Phase 10 nur noch ueber Commands (CommandService),
    damit kein Befehl am State-Guard vorbei den Port erreicht.
    """

    def __init__(self, log: ExecutionLogRepository):
        self._log = log

    @classmethod
    def from_session(cls, db: Session) -> "ActuatorExecutionService":
        return cls(ExecutionLogRepository(db))

    def list_executions(self, limit: int) -> list[ExecutionDto]:
        return executions_to_dtos(self._log.list_recent(limit))
