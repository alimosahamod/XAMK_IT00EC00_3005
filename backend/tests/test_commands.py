from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from application.commands.service import CommandService
from domain.actuators.errors import PolicyViolationError
from domain.commands.errors import InvalidCommandError
from domain.commands.invoker import CommandInvoker
from domain.commands.light import SetLightLevelCommand
from domain.commands.pump import StartPumpCommand, StopPumpCommand
from domain.commands.registry import create_command
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.db import engine
from infrastructure.persistence.models import ActuatorStateRow, CommandLogRow, DeviceRow

# Teil 1: Unit-Tests ohne DB - Zustandsspeicher und command_log sind kleine Fakes.


class FakeStates:
    def __init__(self, state):
        self.state = state

    def get_state(self, device_id):
        return self.state

    def save_state(self, device_id, state):
        self.state = state


class FakeCommandLog:
    def __init__(self):
        self.rows = []

    def add(self, command_type, device_id, payload, status, error_message):
        self.rows.append((command_type, status, error_message))


class BlockingPort(SimulationActuatorAdapter):
    # Simuliert einen Decorator, der den Befehl blockiert (z.B. maxRunTime).
    def apply(self, device_id, command, payload):
        raise PolicyViolationError("maxRunTime", "Max run time exceeded")


def run(command_class, state, payload=None, port=None):
    states = FakeStates(state)
    port = port or SimulationActuatorAdapter()
    log = FakeCommandLog()
    result = CommandInvoker(log).submit(command_class(uuid4(), payload or {}, port, states))
    return result, states, port, log


def test_start_pump_from_idle_succeeds():
    result, states, port, log = run(StartPumpCommand, "idle")
    assert result.status == "success"
    assert states.state == "running"
    assert [a.command for a in port.applied] == ["on"]
    assert log.rows == [("start_pump", "success", None)]


def test_illegal_start_is_rejected_without_port_or_state_change():
    result, states, port, log = run(StartPumpCommand, "maintenance")
    assert result.status == "rejected"
    assert states.state == "maintenance"  # Zustand unveraendert
    assert port.applied == []             # Port nie erreicht
    assert log.rows[0][:2] == ("start_pump", "rejected")


def test_stop_pump_from_running_goes_idle():
    result, states, _, _ = run(StopPumpCommand, "running")
    assert result.status == "success"
    assert states.state == "idle"


def test_port_failure_is_logged_as_failed_and_keeps_state():
    result, states, _, log = run(StartPumpCommand, "idle", port=BlockingPort())
    assert result.status == "failed"
    assert result.error_message == "Max run time exceeded"
    assert states.state == "idle"
    assert log.rows == [("start_pump", "failed", "Max run time exceeded")]


def test_set_light_level_while_running_keeps_state():
    result, states, port, _ = run(SetLightLevelCommand, "running", {"level": 70})
    assert result.status == "success"
    assert states.state == "running"
    assert port.applied[0].payload == {"level": 70}


def test_set_light_level_from_idle_turns_light_on():
    result, states, _, _ = run(SetLightLevelCommand, "idle", {"level": 30})
    assert result.status == "success"
    assert states.state == "running"


def test_set_light_level_rejected_in_error_state():
    result, states, _, _ = run(SetLightLevelCommand, "error", {"level": 30})
    assert result.status == "rejected"
    assert states.state == "error"


@pytest.mark.parametrize("payload", [{}, {"level": 101}, {"level": "high"}, {"level": True}])
def test_set_light_level_invalid_payload(payload):
    with pytest.raises(InvalidCommandError):
        SetLightLevelCommand(uuid4(), payload, SimulationActuatorAdapter(), FakeStates("idle"))


def test_registry_maps_type_to_class_and_rejects_unknown():
    port, states = SimulationActuatorAdapter(), FakeStates("idle")
    assert isinstance(create_command("start_pump", uuid4(), {}, port, states), StartPumpCommand)
    with pytest.raises(InvalidCommandError):
        create_command("fly_to_moon", uuid4(), {}, port, states)


# Teil 2: Integrationstests gegen Postgres mit echtem Decorator-Stapel (build_actuator).
# Alles laeuft in einer Transaktion und wird am Ende zurueckgerollt.


@pytest.fixture
def db():
    try:
        connection = engine.connect()
    except OperationalError:
        pytest.skip("Postgres is not reachable")
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def new_actuator(db, state: str):
    device = DeviceRow(device_type="water_pump", role="actuator", display_name="Test pump")
    db.add(device)
    db.flush()
    db.add(ActuatorStateRow(device_id=device.id, state=state))
    db.commit()
    return device.id


def stored_state(db, device_id) -> str:
    db.expire_all()
    return db.get(ActuatorStateRow, device_id).state


def log_rows(db, device_id) -> list[CommandLogRow]:
    db.expire_all()
    return list(db.scalars(select(CommandLogRow).where(CommandLogRow.device_id == device_id)))


def test_start_pump_transitions_to_running(db):
    device_id = new_actuator(db, "idle")

    result = CommandService.from_session(db).submit("start_pump", device_id)

    assert result.status == "success"
    assert stored_state(db, device_id) == "running"
    rows = log_rows(db, device_id)
    assert [(r.command_type, r.status, r.error_message) for r in rows] == [("start_pump", "success", None)]


def test_illegal_command_rejected_logged(db):
    device_id = new_actuator(db, "maintenance")

    result = CommandService.from_session(db).submit("start_pump", device_id)

    assert result.status == "rejected"
    assert stored_state(db, device_id) == "maintenance"  # actuator_states unveraendert
    rows = log_rows(db, device_id)
    assert [(r.command_type, r.status) for r in rows] == [("start_pump", "rejected")]
    assert "not allowed" in rows[0].error_message
