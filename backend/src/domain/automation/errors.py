class UnknownStrategyError(ValueError):
    """Zu einem strategy_key gibt es keine Strategie.

    Wird von get_strategy() geworfen, also bevor decide() ueberhaupt laeuft.
    Der API-Layer uebersetzt diesen Fehler spaeter in ein 400.
    """
