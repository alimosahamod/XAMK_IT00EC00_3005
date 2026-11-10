from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from application.actuators.dto import ApplyRequestDto, ExecutionDto
from application.actuators.execution_service import ActuatorExecutionService
from domain.actuators.errors import PolicyViolationError
from domain.devices.errors import DeviceNotFoundError
from infrastructure.db import get_db

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


@router.post(
    "/{device_id}/apply",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Actuator not found"},
        409: {"description": "Blocked by a policy decorator (e.g. maxRunTime)"},
    },
)
def apply_command(
    device_id: UUID,
    body: ApplyRequestDto,
    service: ActuatorExecutionService = Depends(get_service),
) -> None:
    """Schickt einen Befehl durch den dekorierten Port (Demo; ab Phase 10 ueber Command).

    Der Router enthaelt keine Policy-Pruefung. Er uebersetzt nur Fehler in HTTP.
    """
    try:
        service.apply(device_id, body.command, body.payload)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PolicyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
