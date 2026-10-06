class SensorReadError(ValueError):
    """Ein Adapter konnte keinen gueltigen Messwert liefern.

    Beispiele: der Vendor meldet einen Fehlerstatus, der Geraetetyp ist
    unbekannt, oder das Geraet ist gar kein Sensor. Der API-Layer
    uebersetzt diesen Fehler in ein 400.
    """
