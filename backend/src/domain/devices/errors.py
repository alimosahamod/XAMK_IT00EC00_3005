class DeviceNotFoundError(LookupError):
    """Es gibt kein Geraet mit dieser id. Der API-Layer macht daraus ein 404."""
