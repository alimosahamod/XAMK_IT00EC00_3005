from uuid import UUID

from application.automation.dto import AutomationRuleDto, RecommendationDto
from domain.automation.context import LocationAutomationContext
from domain.automation.errors import (
    AutomationNotReadyError,
    LocationNotFoundError,
    SensorLinkError,
)
from domain.automation.strategy import IRRIGATE, get_strategy
from domain.devices.errors import DeviceNotFoundError
from infrastructure.persistence.automation_repository import AutomationRuleRepository
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.location_repository import LocationRepository
from infrastructure.persistence.reading_repository import ReadingRepository

MOISTURE_SENSOR = "moisture_sensor"


class AutomationService:
    """Use Case: gespeicherten key laden -> Kontext bauen -> decide() -> DTO.

    Der Service waehlt die Strategie nur ueber get_strategy(key) aus.
    Er kennt keine Formel und hat kein if conservative / if aggressive.
    """

    def __init__(
        self,
        rules: AutomationRuleRepository,
        locations: LocationRepository,
        readings: ReadingRepository,
        devices: DeviceRepository,
    ):
        self._rules = rules
        self._locations = locations
        self._readings = readings
        self._devices = devices

    def get_rule(self, location_id: UUID) -> AutomationRuleDto:
        self._require_location(location_id)
        return AutomationRuleDto(
            location_id=location_id,
            strategy_key=self._rules.get_strategy_key(location_id),
        )

    def set_strategy(self, location_id: UUID, strategy_key: str) -> AutomationRuleDto:
        self._require_location(location_id)
        # Unbekannter key -> UnknownStrategyError, es wird nichts gespeichert.
        get_strategy(strategy_key)
        saved_key = self._rules.upsert(location_id, strategy_key)
        return AutomationRuleDto(location_id=location_id, strategy_key=saved_key)

    def link_sensor(self, location_id: UUID, device_id: UUID) -> None:
        """Ordnet einen Feuchtesensor dem Standort zu, damit evaluate seine Werte nutzt."""
        self._require_location(location_id)
        device = self._devices.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device {device_id} not found")
        if device.device_type != MOISTURE_SENSOR:
            raise SensorLinkError(f"Device {device_id} is not a moisture sensor")
        self._devices.assign_location(device_id, location_id)

    def evaluate(self, location_id: UUID) -> RecommendationDto:
        self._require_location(location_id)

        # 1. Immer der gespeicherte key, nie einer aus dem Request.
        strategy_key = self._rules.get_strategy_key(location_id)
        if strategy_key is None:
            raise AutomationNotReadyError("No strategy saved for this location. Save one first.")
        strategy = get_strategy(strategy_key)

        # 2. Grenzen aus zones, Feuchte aus sensor_readings - keine Konstanten.
        zones = self._locations.list_zone_thresholds(location_id)
        if not zones:
            raise AutomationNotReadyError("This location has no zones with thresholds.")
        moisture = self._readings.latest_value_for_location(location_id, MOISTURE_SENSOR)
        if moisture is None:
            raise AutomationNotReadyError(
                "No moisture reading for this location. Link a moisture sensor and read it first."
            )

        # 3. Ein Kontext pro Zone: gleiche Feuchte, aber die Grenzen dieser Zone.
        results = []
        for zone_name, low, high in zones:
            context = LocationAutomationContext(
                location_id=location_id,
                moisture=moisture,
                threshold_low=low,
                threshold_high=high,
            )
            results.append((zone_name, strategy.decide(context)))

        # 4. Braucht eine Zone Wasser, gewinnt diese Empfehlung, sonst die erste.
        zone_name, recommendation = next(
            ((name, rec) for name, rec in results if rec.action == IRRIGATE),
            results[0],
        )
        return RecommendationDto(
            location_id=location_id,
            strategy_key=strategy_key,
            action=recommendation.action,
            reason=f"{zone_name}: {recommendation.reason}",
        )

    def _require_location(self, location_id: UUID) -> None:
        if not self._locations.exists(location_id):
            raise LocationNotFoundError(f"Location {location_id} not found")
