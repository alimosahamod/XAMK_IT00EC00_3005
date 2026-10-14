from uuid import UUID

from sqlalchemy.orm import Session

from application.automation.service import AutomationService
from application.overview.dto import (
    DeviceCountsDto,
    LastRecommendationDto,
    LocationOverviewDto,
    LocationSummaryDto,
    ReadingSummaryDto,
)
from domain.automation.errors import AutomationNotReadyError, LocationNotFoundError
from infrastructure.persistence.automation_repository import AutomationRuleRepository
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.location_repository import LocationRepository
from infrastructure.persistence.reading_repository import ReadingRepository


class LocationOverviewFacade:

    def __init__(
        self,
        locations: LocationRepository,
        devices: DeviceRepository,
        readings: ReadingRepository,
        automation: AutomationService,
    ):
        self._locations = locations
        self._devices = devices
        self._readings = readings
        self._automation = automation

    @classmethod
    def from_session(cls, db: Session) -> "LocationOverviewFacade":

        locations = LocationRepository(db)
        devices = DeviceRepository(db)
        readings = ReadingRepository(db)
        automation = AutomationService(
            AutomationRuleRepository(db), locations, readings, devices
        )
        return cls(locations, devices, readings, automation)

    def get_overview(self, location_id: UUID) -> LocationOverviewDto:
        # Jeder Aufruf liest frisch aus der DB, nichts wird gecacht: ein neuer
        # Messwert oder eine neue Strategie ist beim naechsten GET sichtbar.
        # Die Anzahl Queries ist konstant und waechst nicht mit der Zahl der Geraete.
        name = self._locations.get_name(location_id)
        if name is None:
            raise LocationNotFoundError(f"Location {location_id} not found")

        counts = self._devices.count_by_role(location_id)
        readings = self._readings.latest_per_device_for_location(location_id)
        strategy_key = self._automation.get_rule(location_id).strategy_key

        return LocationOverviewDto(
            location=LocationSummaryDto(id=location_id, name=name),
            device_counts=DeviceCountsDto(
                sensor=counts.get("sensor", 0),
                actuator=counts.get("actuator", 0),
            ),
            latest_readings=[
                ReadingSummaryDto(
                    device_id=r.device_id,
                    value=r.value,
                    unit=r.unit,
                    recorded_at=r.recorded_at,
                )
                for r in readings
            ],
            strategy_key=strategy_key,
            last_recommendation=self._last_recommendation(location_id),
        )

    def _last_recommendation(self, location_id: UUID) -> LastRecommendationDto | None:

        try:
            recommendation = self._automation.evaluate(location_id)
        except AutomationNotReadyError:
            return None
        return LastRecommendationDto(action=recommendation.action, reason=recommendation.reason)
