class IllegalTransitionError(ValueError):
    """Der Zielzustand ist vom aktuellen Zustand aus nicht erlaubt.

    Wird geworfen, bevor irgendetwas gespeichert wird. Der API-Layer macht daraus ein 409.
    """

    def __init__(self, current: str, target: str, allowed: list[str]):
        self.current = current
        self.target = target
        super().__init__(
            f"Illegal transition {current} -> {target}. "
            f"Allowed from {current}: {', '.join(allowed) or 'none'}"
        )
