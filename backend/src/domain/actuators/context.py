from domain.actuators.errors import IllegalTransitionError
from domain.actuators.state import ActuatorState, get_state


class ActuatorContext:
    """Haelt den aktuellen Zustand eines Aktuators und bewacht jeden Wechsel.

    Der Context entscheidet nicht selbst mit if/elif, was erlaubt ist -
    er fragt das aktuelle Zustandsobjekt. Nur transition() darf den
    Zustand aendern, damit kein Wechsel an der Pruefung vorbei passiert.
    """

    def __init__(self, state: str):
        self._state: ActuatorState = get_state(state)

    @property
    def state(self) -> str:
        return self._state.name

    def allowed_commands(self) -> list[str]:
        return self._state.allowed_commands()

    def transition(self, target: str) -> None:
        # Guard: erst pruefen, dann wechseln. Bei einem Fehler bleibt alles wie vorher.
        if target not in self._state.allowed_targets():
            raise IllegalTransitionError(self.state, target, self._state.allowed_targets())
        self._state = get_state(target)
