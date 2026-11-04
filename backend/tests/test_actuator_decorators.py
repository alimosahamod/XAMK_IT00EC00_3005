from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.actuators.errors import PolicyViolationError
from infrastructure.adapters.actuators.logging_decorator import LoggingActuatorDecorator
from infrastructure.adapters.actuators.max_runtime_decorator import MaxRunTimeActuatorDecorator
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter

# Unit-Tests ohne DB: Repositories werden durch kleine Fakes ersetzt.

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class FakeStates:
    def __init__(self, running_since):
        self.running_since = running_since

    def get_running_since(self, device_id):
        return self.running_since


class FakeLog:
    def __init__(self):
        self.rows = []

    def add(self, device_id, success, policy_applied, message):
        self.rows.append((device_id, success, policy_applied, message))


def build(running_since):
    # Gleiche Reihenfolge wie im Composition Root: Logging -> MaxRunTime -> Simulation.
    sim = SimulationActuatorAdapter()
    log = FakeLog()
    max_rt = MaxRunTimeActuatorDecorator(
        sim, FakeStates(running_since), timedelta(minutes=30), now=lambda: NOW
    )
    return LoggingActuatorDecorator(max_rt, log), sim, log


def test_max_runtime_does_not_call_inner():
    actuator, sim, _ = build(running_since=NOW - timedelta(hours=1))
    with pytest.raises(PolicyViolationError):
        actuator.apply(uuid4(), "on", {})
    assert sim.applied == []  # innerer Adapter wurde nie erreicht


def test_failed_policy_writes_execution_row():
    device_id = uuid4()
    actuator, _, log = build(running_since=NOW - timedelta(hours=1))
    with pytest.raises(PolicyViolationError):
        actuator.apply(device_id, "on", {})
    assert log.rows == [(device_id, False, ["maxRunTime", "logging"], "Max run time exceeded")]


def test_allowed_apply_reaches_inner_and_logs_success():
    device_id = uuid4()
    actuator, sim, log = build(running_since=NOW - timedelta(minutes=5))
    actuator.apply(device_id, "on", {"duration_s": 30})
    assert len(sim.applied) == 1
    assert log.rows == [(device_id, True, ["maxRunTime", "logging"], None)]
