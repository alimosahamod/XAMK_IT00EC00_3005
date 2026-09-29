from application.locations.dto import (
    BuildLocationConfigRequestDto,
    LocationConfigDto,
    LocationDto,
    ZoneDto,
)
from domain.locations.config_builder import LocationConfigBuilder
from domain.locations.entity import LocationConfig
from infrastructure.persistence.models import LocationRow, ZoneRow


def request_to_config(request: BuildLocationConfigRequestDto) -> LocationConfig:
    """Uebersetzt das Request-DTO in Builder-Aufrufe.

    Der Builder bleibt der einzige Weg zu einer `LocationConfig`; das DTO
    wird nie direkt in eine Domain-Entitaet umgegossen.
    """
    builder = LocationConfigBuilder().with_location_name(request.location_name)
    for zone in request.zones:
        builder.add_zone(
            name=zone.name,
            moisture_threshold_low=zone.moisture_threshold_low,
            moisture_threshold_high=zone.moisture_threshold_high,
            schedule=zone.schedule,
        )
    # Wirft ConfigurationError, wenn die Konfiguration ungueltig ist.
    return builder.build()


def rows_to_dto(location_row: LocationRow, zone_rows: list[ZoneRow]) -> LocationConfigDto:
    """Wandelt die gespeicherten Zeilen in das API-Lesemodell um."""
    return LocationConfigDto(
        location=LocationDto(id=location_row.id, name=location_row.name),
        zones=[_zone_row_to_dto(row) for row in zone_rows],
    )


def _zone_row_to_dto(row: ZoneRow) -> ZoneDto:
    return ZoneDto(
        id=row.id,
        location_id=row.location_id,
        name=row.name,
        # Numeric kommt als Decimal aus der DB, das API-Kontrakt ist float.
        moisture_threshold_low=float(row.moisture_threshold_low),
        moisture_threshold_high=float(row.moisture_threshold_high),
        schedule=row.schedule or {},
    )
