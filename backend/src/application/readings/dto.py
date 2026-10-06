from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReadingDto(BaseModel):
    """Lesemodell eines Messwerts fuer die HTTP-Schicht.

    Gleiche Form fuer alle Adapter - der Client sieht nie Vendor-Felder.
    """

    device_id: UUID
    value: float
    unit: str
    source: str
    recorded_at: datetime
