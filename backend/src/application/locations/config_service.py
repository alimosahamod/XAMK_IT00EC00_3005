from uuid import UUID

from application.locations.dto import BuildLocationConfigRequestDto, LocationConfigDto
from application.locations.mappers import request_to_config, rows_to_dto
from infrastructure.persistence.location_repository import LocationRepository


class LocationConfigService:
    """Verbindet den Builder mit dem Repository.

    Reihenfolge ist hier wichtig: erst bauen und pruefen, dann speichern.
    Wirft `build()` einen ConfigurationError, wird das Repository nie
    aufgerufen und es landet nichts in der Datenbank.
    """

    def __init__(self, repo: LocationRepository):
        self._repo = repo

    def build_and_save(self, request: BuildLocationConfigRequestDto) -> LocationConfigDto:
        config = request_to_config(request)
        location_row, zone_rows = self._repo.save_config(config)
        return rows_to_dto(location_row, zone_rows)

    def get_config(self, location_id: UUID) -> LocationConfigDto | None:
        result = self._repo.get_config(location_id)
        if result is None:
            return None
        location_row, zone_rows = result
        return rows_to_dto(location_row, zone_rows)
