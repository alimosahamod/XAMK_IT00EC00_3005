from uuid import UUID

from sqlalchemy.orm import Session

from application.actuators.actuator_chain import build_actuator
from application.actuators.dto import ExecutionDto
from application.actuators.mappers import executions_to_dtos
from domain.actuators.ports import ActuatorPort
from domain.devices.errors import DeviceNotFoundError
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository


class ActuatorExecutionService:
    """Fuehrt Befehle ueber den dekorierten Port aus und liest das Execution-Log.

    Der Service bekommt nur einen `ActuatorPort`. Wie viele Decorators darin
    stecken, weiss er nicht - das entscheidet allein `build_actuator`.
    """

    def __init__(self, devices: DeviceRepository, actuator: ActuatorPort, log: ExecutionLogRepository):
        self._devices = devices
        self._actuator = actuator
        self._log = log

    @classmethod
    def from_session(cls, db: Session) -> "ActuatorExecutionService":
        return cls(DeviceRepository(db), build_actuator(db), ExecutionLogRepository(db))

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        # Nur echte Aktuatoren duerfen Befehle bekommen -> sonst 404.
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(f"No actuator with id {device_id}")
        # Ab hier laeuft alles durch den Decorator-Stapel (Logging -> MaxRunTime -> Simulation).
        # Ein blockierter Versuch wirft PolicyViolationError, ist aber schon geloggt.
        self._actuator.apply(device_id, command, payload)

    def list_executions(self, limit: int) -> list[ExecutionDto]:
        return executions_to_dtos(self._log.list_recent(limit))
