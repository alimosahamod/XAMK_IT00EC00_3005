from uuid import UUID

from pydantic import BaseModel


class SetStrategyRequestDto(BaseModel):
    """Body fuer PUT /api/locations/{location_id}/automation."""

    strategy_key: str


class AutomationRuleDto(BaseModel):
    """Gespeicherte Strategie eines Standorts; None, wenn noch keine gewaehlt ist."""

    location_id: UUID
    strategy_key: str | None


class RecommendationDto(BaseModel):
    """Antwort von evaluate: genau eine Empfehlung fuer den Standort."""

    location_id: UUID
    strategy_key: str
    action: str
    reason: str
