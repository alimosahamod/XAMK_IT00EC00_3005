from uuid import uuid4

import pytest

from application.automation.service import AutomationService
from domain.automation.errors import (
    AutomationNotReadyError,
    LocationNotFoundError,
    UnknownStrategyError,
)

# Fakes statt echter Repositories: so laeuft der Service ohne Datenbank.


class FakeRules:
    def __init__(self, key=None):
        self.key = key

    def get_strategy_key(self, location_id):
        return self.key

    def upsert(self, location_id, strategy_key, parameters=None):
        self.key = strategy_key
        return strategy_key


class FakeLocations:
    def __init__(self, location_id, zones):
        self.location_id = location_id
        self.zones = zones

    def exists(self, location_id):
        return location_id == self.location_id

    def list_zone_thresholds(self, location_id):
        return self.zones


class FakeReadings:
    def __init__(self, moisture):
        self.moisture = moisture

    def latest_value_for_location(self, location_id, device_type):
        return self.moisture


def make_service(location_id, key=None, moisture=0.30, zones=None):
    if zones is None:
        zones = [("Bench 1", 0.25, 0.45)]
    return AutomationService(
        FakeRules(key), FakeLocations(location_id, zones), FakeReadings(moisture), devices=None
    )


def test_evaluate_uses_saved_key():
    location_id = uuid4()
    service = make_service(location_id)

    service.set_strategy(location_id, "conservative")
    first = service.evaluate(location_id)
    service.set_strategy(location_id, "aggressive")
    second = service.evaluate(location_id)

    # Gleiche Feuchte, gleiche Zone - nur der gespeicherte key hat sich geaendert.
    assert (first.strategy_key, first.action) == ("conservative", "wait")
    assert (second.strategy_key, second.action) == ("aggressive", "irrigate")
    assert first.reason.startswith("Bench 1: ")


def test_thresholds_come_from_zone():
    location_id = uuid4()
    # Gleiche Feuchte 0.30, aber die Zone hat ein hoeheres Band.
    service = make_service(location_id, key="conservative", zones=[("Wet bench", 0.35, 0.60)])

    assert service.evaluate(location_id).action == "irrigate"


def test_zone_that_needs_water_wins():
    location_id = uuid4()
    zones = [("A dry-tolerant", 0.10, 0.40), ("B thirsty", 0.35, 0.60)]
    service = make_service(location_id, key="conservative", zones=zones)

    result = service.evaluate(location_id)

    assert result.action == "irrigate"
    assert result.reason.startswith("B thirsty: ")


def test_unknown_key_is_not_saved():
    location_id = uuid4()
    service = make_service(location_id, key="conservative")

    with pytest.raises(UnknownStrategyError):
        service.set_strategy(location_id, "random")
    assert service.get_rule(location_id).strategy_key == "conservative"


def test_missing_location_raises():
    service = make_service(uuid4(), key="conservative")

    with pytest.raises(LocationNotFoundError):
        service.evaluate(uuid4())


def test_evaluate_without_saved_key_raises():
    location_id = uuid4()

    with pytest.raises(AutomationNotReadyError):
        make_service(location_id, key=None).evaluate(location_id)


def test_evaluate_without_reading_raises():
    location_id = uuid4()

    with pytest.raises(AutomationNotReadyError):
        make_service(location_id, key="conservative", moisture=None).evaluate(location_id)
