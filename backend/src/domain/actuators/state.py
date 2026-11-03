from abc import ABC
from typing import ClassVar

# Jeder neue Aktuator startet in diesem Zustand (auch der Seed in der Migration).
INITIAL_STATE = "idle"


class ActuatorState(ABC):
    """Gemeinsames Interface aller Aktuator-Zustaende.

    Jeder Zustand kennt nur seine eigenen Befehle: Befehlsname -> Zielzustand.
    Daraus folgen beide Antworten, die der Context braucht:
    "Welche Befehle gehen jetzt?" und "Wohin darf ich wechseln?".
    """

    name: ClassVar[str]
    commands: ClassVar[dict[str, str]]

    def allowed_commands(self) -> list[str]:
        return list(self.commands)

    def allowed_targets(self) -> list[str]:
        return list(self.commands.values())


class OffState(ActuatorState):
    # Ausgeschaltet: man kann den Aktuator nur wieder einschalten.
    name = "off"
    commands = {"power_on": "idle"}


class IdleState(ActuatorState):
    # Bereit: von hier aus ist fast alles moeglich.
    name = "idle"
    commands = {
        "start": "running",
        "start_maintenance": "maintenance",
        "report_fault": "error",
        "power_off": "off",
    }


class RunningState(ActuatorState):
    # Laeuft: erst stoppen, bevor Wartung oder Ausschalten moeglich ist.
    name = "running"
    commands = {"stop": "idle", "report_fault": "error"}


class ErrorState(ActuatorState):
    # Fehler: zuruecksetzen oder in die Wartung schicken.
    name = "error"
    commands = {"reset": "idle", "start_maintenance": "maintenance"}


class MaintenanceState(ActuatorState):
    # Wartung: nur das Beenden der Wartung fuehrt zurueck nach idle.
    name = "maintenance"
    commands = {"finish_maintenance": "idle"}


# Registry: Zustandsname (so wie in der DB gespeichert) -> Zustandsobjekt.
_STATES: dict[str, ActuatorState] = {
    state.name: state
    for state in (OffState(), IdleState(), RunningState(), ErrorState(), MaintenanceState())
}


def get_state(name: str) -> ActuatorState:
    """Liefert das Zustandsobjekt zu einem gespeicherten Namen."""
    try:
        return _STATES[name]
    except KeyError:
        raise ValueError(f"Unknown actuator state: {name}")
