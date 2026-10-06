from datetime import UTC, datetime
from uuid import UUID

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading

# Vendor-Kanalnamen fuer unsere Geraetetypen.
_CHANNELS = {"moisture_sensor": "SOIL_MOIST", "light_sensor": "AMB_LIGHT"}


class VendorSensorClient:
    """Stub fuer ein fremdes Vendor-SDK (Adaptee).

    Das SDK spricht seine eigene Sprache: andere Feldnamen, Prozent statt
    Anteil, Kilolux statt Lux, Zeit als Epoch-Millisekunden und ein
    Statusfeld. Genau diese fremde Form soll die Anwendung nie sehen.
    """

    def fetch(self, sensor_ref: str, device_type: str) -> dict:
        channel = _CHANNELS.get(device_type, "UNKNOWN")
        if channel == "SOIL_MOIST":
            return {"sensorRef": sensor_ref, "ch": channel, "val": 31.5, "uom": "PCT",
                    "tsMillis": _now_millis(), "status": "OK"}
        if channel == "AMB_LIGHT":
            return {"sensorRef": sensor_ref, "ch": channel, "val": 12.4, "uom": "KLX",
                    "tsMillis": _now_millis(), "status": "OK"}
        return {"sensorRef": sensor_ref, "ch": channel, "status": "E_NO_CHANNEL"}


def _now_millis() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


# Vendor-Einheit -> (unsere Einheit, Umrechnungsfaktor).
_UNIT_MAP: dict[str, tuple[str, float]] = {
    "PCT": ("vwc", 0.01),  # 31.5 % -> 0.315 vwc
    "KLX": ("lux", 1000.0),  # 12.4 klx -> 12400 lux
}


class VendorStubSensorAdapter(SensorPort):
    """Adapter: uebersetzt die Vendor-Antwort in unseren `Reading`.

    Er uebersetzt nur (Namen, Einheiten, Zeit, Status). Ob bewaessert wird,
    entscheidet er nicht - das ist spaeter Aufgabe der Strategy.
    """

    def __init__(self, client: VendorSensorClient | None = None):
        self._client = client or VendorSensorClient()

    def read(self, device: Device) -> Reading:
        if device.id is None:
            raise SensorReadError("Cannot read an unsaved device")
        raw = self._client.fetch(str(device.id), device.device_type)
        return translate_vendor_payload(raw)


def translate_vendor_payload(raw: dict) -> Reading:
    """Reine Uebersetzung ohne I/O, damit sie ohne HTTP testbar ist."""
    if raw.get("status") != "OK":
        raise SensorReadError(f"Vendor reported status {raw.get('status')!r}")
    try:
        unit, factor = _UNIT_MAP[raw["uom"]]
        return Reading(
            device_id=UUID(raw["sensorRef"]),
            value=round(float(raw["val"]) * factor, 4),
            unit=unit,
            source="vendor",
            recorded_at=datetime.fromtimestamp(raw["tsMillis"] / 1000, tz=UTC),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SensorReadError(f"Vendor payload cannot be translated: {exc}")
