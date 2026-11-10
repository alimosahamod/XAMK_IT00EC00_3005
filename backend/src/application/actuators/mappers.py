from application.actuators.dto import ExecutionDto
from infrastructure.persistence.models import ActuatorExecutionLogRow


def execution_to_dto(row: ActuatorExecutionLogRow) -> ExecutionDto:
    """Wandelt eine Log-Zeile aus der DB in das API-Lesemodell um."""
    return ExecutionDto(
        id=row.id,
        device_id=row.device_id,
        success=row.success,
        policy_applied=list(row.policy_applied),
        message=row.message,
        created_at=row.created_at,
    )


def executions_to_dtos(rows: list[ActuatorExecutionLogRow]) -> list[ExecutionDto]:
    return [execution_to_dto(row) for row in rows]
