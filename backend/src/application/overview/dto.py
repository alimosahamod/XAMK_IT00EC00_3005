from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Lesemodell fuer GET /api/locations/{location_id}/overview (Phase 7).
# Die Feldnamen sind der JSON-Vertrag mit dem Dashboard und tauchen 1:1 in
# Scalar auf - umbenennen nur zusammen mit dem Frontend.


class LocationSummaryDto(BaseModel):

    id: UUID
    name: str


class DeviceCountsDto(BaseModel):

    sensor: int = Field(description="Sensors linked to this location")
    actuator: int = Field(description="Actuators linked to this location")


class ReadingSummaryDto(BaseModel):

    device_id: UUID
    value: float
    unit: str
    recorded_at: datetime


class LastRecommendationDto(BaseModel):

    action: str = Field(description='"irrigate" or "wait"')
    reason: str


class LocationOverviewDto(BaseModel):

    location: LocationSummaryDto
    device_counts: DeviceCountsDto
    latest_readings: list[ReadingSummaryDto] = Field(
        description="Newest reading per sensor at this location, newest first"
    )
    strategy_key: str | None = Field(description="Saved strategy; null if none was chosen")
    last_recommendation: LastRecommendationDto | None = Field(
        description="Computed on every request via the automation service; "
        "null while strategy, zone or moisture reading is missing"
    )
