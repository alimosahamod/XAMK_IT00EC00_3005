from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# JSON-Vertrag fuer /api/commands (Phase 10). Die Feldnamen nutzt das Dashboard.

STATUS_DESCRIPTION = "success | failed | rejected"


class CommandRequestDto(BaseModel):
    """Body fuer POST /api/commands: welcher Befehl, fuer welches Geraet, mit welchen Daten."""

    command_type: str = Field(
        description="start_pump | stop_pump | set_light_level | switch_off_light", examples=["start_pump"]
    )
    device_id: UUID
    payload: dict = Field(
        default_factory=dict,
        description='Command data, e.g. {"level": 70} for set_light_level',
        examples=[{}],
    )


class CommandResultDto(BaseModel):
    """Antwort auf POST /api/commands: wie der Versuch ausgegangen ist (steht so auch im command_log)."""

    command_type: str
    device_id: UUID
    payload: dict
    status: str = Field(description=STATUS_DESCRIPTION, examples=["success"])
    error_message: str | None = Field(
        default=None, examples=["Command start_pump not allowed in state maintenance. Allowed: finish_maintenance"]
    )


class CommandLogDto(BaseModel):
    """Eine Zeile aus command_log fuer GET /api/commands."""

    id: UUID
    command_type: str
    device_id: UUID
    payload: dict
    status: str = Field(description=STATUS_DESCRIPTION, examples=["rejected"])
    error_message: str | None = None
    created_at: datetime
