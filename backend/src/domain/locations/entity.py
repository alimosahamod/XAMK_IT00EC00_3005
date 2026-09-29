from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Zone:
    """Ein Bereich innerhalb eines Standorts mit eigenen Feuchte-Grenzen.

    frozen=True: nach dem Bauen darf niemand mehr an den Werten drehen,
    sonst waere die vom Builder gepruefte Konfiguration nicht mehr gueltig.
    """

    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: dict
    id: UUID | None = None


@dataclass(frozen=True)
class Location:
    """Ein Standort mit seinen Zonen."""

    name: str
    # tuple statt list: das Ergebnis des Builders soll nicht nachtraeglich
    # um eine ungepruefte Zone erweitert werden koennen.
    zones: tuple[Zone, ...]
    id: UUID | None = None


@dataclass(frozen=True)
class LocationConfig:
    """Das fertige Produkt des Builders: ein geprueftes Gesamtpaket."""

    location: Location
