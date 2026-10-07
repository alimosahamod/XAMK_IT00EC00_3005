from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LocationAutomationContext:
    """Alles, was eine Strategie fuer ihre Entscheidung wissen darf.

    Reine Domain: nur Zahlen, keine ORM-Zeilen. Der Service baut den Kontext
    aus sensor_readings (Feuchte) und zones (Grenzen) zusammen. Die Strategie
    weiss nicht, woher die Werte kommen - deshalb laesst sie sich auch mit
    einem kuenstlichen Kontext im Test pruefen.
    """

    location_id: UUID
    moisture: float  # letzter Feuchtewert (vwc)
    threshold_low: float  # aus zones, nicht hart kodiert
    threshold_high: float
    light: float | None = None  # optional, aktuell von keiner Strategie genutzt


@dataclass(frozen=True)
class Recommendation:
    """Ergebnis von decide(): nur eine Empfehlung, keine Ausfuehrung.

    Die Strategie startet selbst keine Pumpe. Wer die Empfehlung umsetzt,
    entscheidet eine spaetere Schicht.
    """

    action: str  # "irrigate" oder "wait"
    reason: str
    score: float | None = None
