from typing import Literal
from uuid import UUID

from pydantic import BaseModel


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
