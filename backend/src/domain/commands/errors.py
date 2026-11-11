class CommandRejectedError(Exception):
    """Der Befehl ist im aktuellen Zustand nicht erlaubt (State-Guard aus Phase 8).

    Der Invoker macht daraus status="rejected". Port und Zustand bleiben unberuehrt.
    """

    def __init__(self, command_type: str, current: str, allowed: list[str]):
        self.current = current
        super().__init__(
            f"Command {command_type} not allowed in state {current}. "
            f"Allowed: {', '.join(allowed) or 'none'}"
        )


class InvalidCommandError(ValueError):
    """Unbekannter command_type oder ungueltiger Payload - der Befehl wird gar nicht erst gebaut."""
