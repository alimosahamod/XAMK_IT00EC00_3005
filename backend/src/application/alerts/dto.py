from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# JSON-Vertrag fuer GET /api/alerts (Phase 11). Das Dashboard nutzt diese Feldnamen.


class AlertDto(BaseModel):
    """Ein Alarm aus der Tabelle `alerts`.

    `acknowledged_at` ist zwar eine Spalte, gehoert in dieser Phase aber bewusst
    nicht zur Antwort. Die ids sind None, wenn das Geraet nicht zugewiesen war.
    """

    # Erlaubt AlertDto.model_validate(alert_row) direkt aus der ORM-Zeile.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID | None
    zone_id: UUID | None
    device_id: UUID | None
    severity: str = Field(description="info | warning | critical", examples=["warning"])
    message: str = Field(examples=["Moisture below zone low"])
    event_type: str = Field(
        description="threshold.crossed | command.failed | state.changed", examples=["threshold.crossed"]
    )
    status: str = Field(description="active | resolved", examples=["active"])
    created_at: datetime
