from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Lesemodell fuer GET /api/actuators/executions (Phase 9).
# Die Feldnamen sind der JSON-Vertrag mit dem Dashboard.


class ExecutionDto(BaseModel):
    """Ein Versuch, einen Aktuator auszufuehren - erfolgreich oder blockiert."""

    id: UUID
    device_id: UUID
    success: bool
    policy_applied: list[str] = Field(
        description="Policies of the decorator stack, inner to outer", examples=[["maxRunTime", "logging"]]
    )
    message: str | None = Field(default=None, examples=["Max run time exceeded"])
    created_at: datetime

