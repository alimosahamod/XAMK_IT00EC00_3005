from uuid import UUID

from pydantic import BaseModel, Field


class ZoneRequestDto(BaseModel):
    """Eine Zone, wie sie der Client im Create-Request schickt."""

    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    # Optional, damit eine Zone auch ohne Zeitplan angelegt werden kann.
    schedule: dict = Field(default_factory=dict)


class BuildLocationConfigRequestDto(BaseModel):
    """Request-Modell fuer POST /api/locations/config."""

    location_name: str
    zones: list[ZoneRequestDto] = Field(default_factory=list)


class LocationDto(BaseModel):
    """Lesemodell des Standorts ohne seine Zonen."""

    id: UUID
    name: str


class ZoneDto(BaseModel):
    """Lesemodell einer Zone.

    `location_id` steht bewusst in jeder Zeile: der Client soll die Zone
    ihrem Standort zuordnen koennen, ohne die Verschachtelung auszuwerten.
    """

    id: UUID
    location_id: UUID
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: dict


class LocationConfigDto(BaseModel):
    """Antwort von Create und Read: Standort plus seine Zonen."""

    location: LocationDto
    zones: list[ZoneDto]
