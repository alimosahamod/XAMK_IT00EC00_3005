class ConfigurationError(ValueError):
    """Eine Standort-Konfiguration ist unvollstaendig oder widerspruechlich.

    Die Domain wirft diesen Fehler in `build()`, also bevor irgendetwas
    gespeichert wird. Der API-Layer uebersetzt ihn spaeter in ein 400.
    Eigene Klasse statt nacktem ValueError, damit der Router genau diesen
    Fall abfangen kann und nicht jeden beliebigen ValueError.
    """
