from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from application.commands.dto import CommandLogDto, CommandRequestDto, CommandResultDto
from application.commands.service import CommandService
from domain.commands.errors import InvalidCommandError
from domain.devices.errors import DeviceNotFoundError
from infrastructure.db import get_db

router = APIRouter(prefix="/api/commands", tags=["commands"])


def get_service(db: Session = Depends(get_db)) -> CommandService:
    return CommandService.from_session(db)


@router.post(
    "",
    response_model=CommandResultDto,
    responses={
        200: {
            "description": (
                "The command was processed and written to command_log. "
                "`status` tells the outcome: success, failed (a decorator policy or the adapter "
                "stopped it) or rejected (not in allowed_commands for the current state; "
                "actuator state unchanged). Rejected is deliberately 200, not 409."
            )
        },
        400: {"description": "Unknown command_type or invalid payload (nothing is logged)"},
        404: {"description": "Actuator not found (nothing is logged)"},
    },
)
def submit_command(
    body: CommandRequestDto,
    service: CommandService = Depends(get_service),
) -> CommandResultDto:
    """Fuehrt einen Aktuator-Befehl als Command-Objekt aus.

    Der Router kennt keine einzelnen Befehle und ruft keinen Port auf. Er gibt den
    Request an den Service (Client) weiter und uebersetzt nur Fehler in HTTP.
    """
    try:
        return service.submit(body.command_type, body.device_id, body.payload)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidCommandError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[CommandLogDto])
def list_commands(
    limit: int = Query(default=50, ge=1, le=200, description="Max number of rows, newest first"),
    service: CommandService = Depends(get_service),
) -> list[CommandLogDto]:
    """Befehlshistorie aus command_log: jeder Versuch, auch rejected und failed."""
    return service.list_commands(limit)
