from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceDto(BaseModel):
    """Lesemodell fuer die HTTP-Schicht.

    Das Domain-`Device` ist absichtlich kein DTO: es kennt kein Pydantic und
    darf sich aendern, ohne das API-Schema zu brechen. Die Umwandlung passiert
    nur in `mappers.py`, damit hier keine Mapping-Logik landet.
    """

    id: UUID
    device_type: str
    role: Literal["sensor", "actuator"]
    device_family: str
    display_name: str
    default_config: dict
    # Phase 8: nur bei Aktuatoren gesetzt. allowed_commands beantwortet
    # "was darf ich jetzt tun?", damit das UI nicht selbst raten muss.
    state: str | None = Field(
        default=None, description="off | idle | running | error | maintenance (null for sensors)"
    )
    allowed_commands: list[str] = []


class TransitionRequestDto(BaseModel):
    """Body fuer POST /api/devices/{id}/transition (Demo bis Phase 10 Command)."""

    target: str = Field(description="Target state, e.g. running", examples=["running"])
