from datetime import timedelta

from sqlalchemy.orm import Session

from domain.actuators.ports import ActuatorPort
from infrastructure.adapters.actuators.logging_decorator import LoggingActuatorDecorator
from infrastructure.adapters.actuators.max_runtime_decorator import MaxRunTimeActuatorDecorator
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository
from infrastructure.settings import settings


def build_actuator(db: Session) -> ActuatorPort:
    """Composition Root: baut den Decorator-Stapel an genau einer Stelle.

    Reihenfolge (von aussen nach innen):
        LoggingActuatorDecorator -> MaxRunTimeActuatorDecorator -> SimulationActuatorAdapter

    Logging ist aussen, damit es auch blockierte Versuche sieht.
    Der Aufrufer bekommt nur einen ActuatorPort und kennt die Schichten nicht.
    """
    actuator: ActuatorPort = SimulationActuatorAdapter()
    actuator = MaxRunTimeActuatorDecorator(
        actuator,
        ActuatorStateRepository(db),
        timedelta(seconds=settings.actuator_max_run_time_s),
    )
    return LoggingActuatorDecorator(actuator, ExecutionLogRepository(db))
