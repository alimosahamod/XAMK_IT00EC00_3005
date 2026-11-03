import pytest

from domain.actuators.context import ActuatorContext
from domain.actuators.errors import IllegalTransitionError
from domain.actuators.state import get_state

# Reine Domain-Tests: keine DB, kein HTTP. Nur Context und Zustandsobjekte.

LEGAL_EDGES = [
    ("off", "idle"),
    ("idle", "running"),
    ("idle", "maintenance"),
    ("idle", "error"),
    ("idle", "off"),
    ("running", "idle"),
    ("running", "error"),
    ("error", "idle"),
    ("error", "maintenance"),
    ("maintenance", "idle"),
]

ILLEGAL_EDGES = [
    ("running", "maintenance"),
    ("running", "off"),
    ("off", "running"),
    ("off", "error"),
    ("error", "running"),
    ("maintenance", "running"),
    ("idle", "idle"),
    ("idle", "flying"),  # unbekannter Zielzustand
]


def test_idle_to_running_allowed():
    context = ActuatorContext("idle")
    context.transition("running")
    assert context.state == "running"


def test_running_to_maintenance_rejected():
    context = ActuatorContext("running")
    with pytest.raises(IllegalTransitionError):
        context.transition("maintenance")
    # Nach dem Fehler bleibt der alte Zustand erhalten.
    assert context.state == "running"


@pytest.mark.parametrize("current, target", LEGAL_EDGES)
def test_legal_edges(current, target):
    context = ActuatorContext(current)
    context.transition(target)
    assert context.state == target


@pytest.mark.parametrize("current, target", ILLEGAL_EDGES)
def test_illegal_edges(current, target):
    context = ActuatorContext(current)
    with pytest.raises(IllegalTransitionError):
        context.transition(target)
    assert context.state == current


def test_allowed_commands_follow_the_state():
    context = ActuatorContext("idle")
    assert "start" in context.allowed_commands()

    context.transition("running")
    assert context.allowed_commands() == ["stop", "report_fault"]


def test_every_command_points_to_a_known_state():
    # Schuetzt vor Tippfehlern in der Tabelle: jedes Ziel muss existieren.
    for name in ["off", "idle", "running", "error", "maintenance"]:
        for target in get_state(name).allowed_targets():
            get_state(target)


def test_unknown_stored_state_is_rejected():
    with pytest.raises(ValueError):
        ActuatorContext("broken")
