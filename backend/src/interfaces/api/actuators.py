from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from application.actuators.dto import ExecutionDto
from application.actuators.execution_service import ActuatorExecutionService
from infrastructure.db import get_db

# Phase 10: der Demo-Endpunkt POST /{device_id}/apply ist entfernt. Aktuatoren werden
# nur noch ueber POST /api/commands gesteuert (Command -> State-Guard -> dekorierter Port).
router = APIRouter(prefix="/api/actuators", tags=["actuators"])


def get_service(db: Session = Depends(get_db)) -> ActuatorExecutionService:
    return ActuatorExecutionService.from_session(db)


@router.get("/executions", response_model=list[ExecutionDto])
def list_executions(
    limit: int = Query(default=20, ge=1, le=200, description="Max number of rows, newest first"),
    service: ActuatorExecutionService = Depends(get_service),
) -> list[ExecutionDto]:
    """Execution-Log: jeder Versuch, auch blockierte (success=false)."""
    return service.list_executions(limit)
