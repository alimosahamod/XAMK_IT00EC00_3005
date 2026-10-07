from abc import ABC, abstractmethod

from domain.automation.context import LocationAutomationContext, Recommendation
from domain.automation.errors import UnknownStrategyError

IRRIGATE = "irrigate"
WAIT = "wait"


class AutomationStrategy(ABC):
    """Gemeinsames Interface aller Bewaesserungs-Strategien.

    Der Aufrufer kennt nur decide(context). Welcher Algorithmus dahinter
    steckt, wird ueber den key ausgewaehlt - nicht ueber if/elif im Router.
    """

    key: str

    @abstractmethod
    def decide(self, context: LocationAutomationContext) -> Recommendation:
        """Liefert eine Empfehlung fuer genau diesen Kontext."""


class ConservativeMoistureStrategy(AutomationStrategy):
    """Bewaessert erst, wenn die Feuchte unter die untere Zonengrenze faellt.

    Spart Wasser: solange der Wert im Band low..high liegt, wird gewartet.
    """

    key = "conservative"

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        low, high = context.threshold_low, context.threshold_high
        moisture = context.moisture

        if moisture < low:
            return Recommendation(
                action=IRRIGATE,
                reason=f"Moisture {moisture:.2f} is below {low:.2f}",
                score=round(low - moisture, 4),
            )
        return Recommendation(
            action=WAIT,
            reason=f"Moisture {moisture:.2f} is within {low:.2f}–{high:.2f}"
            if moisture <= high
            else f"Moisture {moisture:.2f} is above {high:.2f}",
        )


class AggressiveMoistureStrategy(AutomationStrategy):
    """Bewaessert schon, wenn die Feuchte unter die Mitte des Bandes faellt.

    Unterschied zu conservative: im Bereich low <= moisture < Mitte
    empfiehlt diese Strategie bereits "irrigate", conservative noch "wait".
    Beispiel low=0.25, high=0.45, moisture=0.30 -> aggressive bewaessert.
    """

    key = "aggressive"

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        low, high = context.threshold_low, context.threshold_high
        moisture = context.moisture
        midpoint = (low + high) / 2

        if moisture < midpoint:
            return Recommendation(
                action=IRRIGATE,
                reason=f"Moisture {moisture:.2f} is below midpoint {midpoint:.2f} "
                f"of {low:.2f}–{high:.2f}",
                score=round(midpoint - moisture, 4),
            )
        return Recommendation(
            action=WAIT,
            reason=f"Moisture {moisture:.2f} is at or above midpoint {midpoint:.2f}",
        )


# Registry statt if/elif: eine neue Strategie = neue Klasse + ein Eintrag hier.
_STRATEGIES: dict[str, AutomationStrategy] = {
    strategy.key: strategy
    for strategy in (ConservativeMoistureStrategy(), AggressiveMoistureStrategy())
}


def available_keys() -> list[str]:
    """Alle bekannten strategy_keys, z.B. fuer Validierung und Dropdown."""
    return list(_STRATEGIES)


def get_strategy(key: str) -> AutomationStrategy:
    """Waehlt die Strategie zum key aus. Unbekannter key -> Fehler vor decide()."""
    try:
        return _STRATEGIES[key]
    except KeyError:
        raise UnknownStrategyError(
            f"Unknown strategy '{key}'. Known: {', '.join(available_keys())}"
        ) from None
