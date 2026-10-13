class UnknownStrategyError(ValueError):
    """Zu einem strategy_key gibt es keine Strategie.

    Wird von get_strategy() geworfen, also bevor decide() ueberhaupt laeuft.
    Der API-Layer uebersetzt diesen Fehler spaeter in ein 400.
    """


class LocationNotFoundError(LookupError):
    """Es gibt keinen Standort mit dieser id. Der API-Layer macht daraus ein 404."""


class AutomationNotReadyError(ValueError):
    """Fuer eine Auswertung fehlt etwas: Strategie, Zone oder Feuchtewert.

    Der Standort existiert, aber decide() kann noch nicht laufen.
    Der API-Layer macht daraus ein 409.
    """


class SensorLinkError(ValueError):
    """Das Geraet kann nicht als Feuchtesensor eines Standorts verknuepft werden.

    Der API-Layer macht daraus ein 400.
    """
