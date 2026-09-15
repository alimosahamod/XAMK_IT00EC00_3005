from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class Sensor:
    """Reiner Domain-Sensor - kein ORM, kein FastAPI, kein Pydantic."""

    device_type: str
    display_name: str | None = None
    default_config: dict = field(default_factory=dict)
    # id ist None, solange der Sensor noch nicht gespeichert wurde.
    id: UUID | None = None
