from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Reading:
    """Normalisierter Messwert - egal welcher Adapter ihn erzeugt hat.

    Reine Domain: kein ORM, kein Pydantic. Jeder Adapter muss genau diese
    Form liefern, damit Service, Datenbank und spaetere Strategy nur eine
    einzige Messwert-Form kennen.
    """

    device_id: UUID
    value: float
    unit: str  # z.B. "vwc" oder "lux"
    source: str  # "simulation" oder "vendor": welcher Adapter gelesen hat
    recorded_at: datetime  # immer mit Zeitzone
