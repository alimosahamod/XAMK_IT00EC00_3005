from uuid import uuid4

import pytest

from domain.automation.context import LocationAutomationContext
from domain.automation.errors import UnknownStrategyError
from domain.automation.strategy import (
    AggressiveMoistureStrategy,
    ConservativeMoistureStrategy,
    available_keys,
    get_strategy,
)


def make_context(moisture: float) -> LocationAutomationContext:
    # Band 0.25-0.45, Mitte 0.35 - wie eine Zone aus Phase 4.
    return LocationAutomationContext(
        location_id=uuid4(),
        moisture=moisture,
        threshold_low=0.25,
        threshold_high=0.45,
    )


def test_conservative_waits_when_within_band():
    result = ConservativeMoistureStrategy().decide(make_context(0.30))

    assert result.action == "wait"
    assert "within" in result.reason


def test_aggressive_differs_on_same_context():
    # Gleicher Kontext, anderer key -> andere Empfehlung.
    context = make_context(0.30)

    conservative = get_strategy("conservative").decide(context)
    aggressive = get_strategy("aggressive").decide(context)

    assert conservative.action == "wait"
    assert aggressive.action == "irrigate"


def test_both_irrigate_below_low():
    context = make_context(0.20)

    assert ConservativeMoistureStrategy().decide(context).action == "irrigate"
    assert AggressiveMoistureStrategy().decide(context).action == "irrigate"


def test_both_wait_above_midpoint():
    context = make_context(0.40)

    assert ConservativeMoistureStrategy().decide(context).action == "wait"
    assert AggressiveMoistureStrategy().decide(context).action == "wait"


def test_get_strategy_returns_matching_key():
    for key in available_keys():
        assert get_strategy(key).key == key


def test_unknown_key_raises():
    with pytest.raises(UnknownStrategyError):
        get_strategy("random")
