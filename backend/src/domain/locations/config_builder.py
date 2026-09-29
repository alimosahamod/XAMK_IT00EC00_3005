from domain.locations.entity import Location, LocationConfig, Zone
from domain.locations.errors import ConfigurationError

# Volumetrischer Wassergehalt (VWC) wird als Anteil angegeben: 0.0 bis 1.0.
MIN_THRESHOLD = 0.0
MAX_THRESHOLD = 1.0


class LocationConfigBuilder:
    """Baut eine `LocationConfig` Schritt fuer Schritt zusammen.

    Warum ein Builder und kein grosser Konstruktor: ein Standort besteht aus
    einem Namen und beliebig vielen Zonen, und die Zonen kommen im UI nach
    und nach dazu. Waehrend des Sammelns ist das Objekt noch unfertig.
    Erst `build()` prueft alles und gibt ein gueltiges Produkt zurueck.
    """

    def __init__(self) -> None:
        self._location_name: str | None = None
        self._zones: list[Zone] = []

    def with_location_name(self, name: str) -> "LocationConfigBuilder":
        self._location_name = name
        return self  # Rueckgabe von self erlaubt das Verketten der Aufrufe.

    def add_zone(
        self,
        name: str,
        moisture_threshold_low: float,
        moisture_threshold_high: float,
        schedule: dict | None = None,
    ) -> "LocationConfigBuilder":
        # Hier wird noch nicht geprueft: der Aufrufer darf erst alles sammeln.
        self._zones.append(
            Zone(
                name=name,
                moisture_threshold_low=moisture_threshold_low,
                moisture_threshold_high=moisture_threshold_high,
                schedule=schedule or {},
            )
        )
        return self

    def build(self) -> LocationConfig:
        """Prueft die gesammelten Angaben und gibt das fertige Produkt zurueck.

        Raises:
            ConfigurationError: sobald eine Regel verletzt ist.
        """
        name = (self._location_name or "").strip()
        if not name:
            raise ConfigurationError("Location name is required")

        if not self._zones:
            raise ConfigurationError("At least one zone is required")

        checked: list[Zone] = []
        for zone in self._zones:
            checked.append(self._validate_zone(zone))

        location = Location(name=name, zones=tuple(checked))
        return LocationConfig(location=location)

    @staticmethod
    def _validate_zone(zone: Zone) -> Zone:
        zone_name = (zone.name or "").strip()
        if not zone_name:
            raise ConfigurationError("Zone name is required")

        low = zone.moisture_threshold_low
        high = zone.moisture_threshold_high

        for label, value in (("low", low), ("high", high)):
            if not MIN_THRESHOLD <= value <= MAX_THRESHOLD:
                raise ConfigurationError(
                    f"Zone '{zone_name}': moisture threshold {label} must be "
                    f"between {MIN_THRESHOLD} and {MAX_THRESHOLD}"
                )

        # Gleiche Werte sind ebenfalls ungueltig: dann gaebe es kein Fenster,
        # in dem die Bewaesserung aus bleiben duerfte.
        if low >= high:
            raise ConfigurationError(
                f"Zone '{zone_name}': moisture threshold low must be lower than high"
            )

        return Zone(
            name=zone_name,
            moisture_threshold_low=low,
            moisture_threshold_high=high,
            schedule=zone.schedule or {},
        )
