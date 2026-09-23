from abc import ABC, abstractmethod

from domain.devices.entity import Device
from domain.sensors.creators import get_creator


# Ein Sensor nimmt Informationen aus der Umgebung auf. Er kann zum Beispiel
# die Feuchtigkeit der Erde oder die Helligkeit messen.
#
# Ein Aktuator macht das Gegenteil: Er fuehrt eine Aktion aus, wenn er einen
# Befehl bekommt. In unserem Gewaechshaus kann er zum Beispiel eine
# Wasserpumpe oder eine Pflanzenlampe einschalten.
#
# Die Factory erstellt Sensoren und Aktuatoren gemeinsam als ein Geraeteset.

# Gemeinsame Schnittstelle für alle Gerätefamilien.
# Jede konkrete Factory muss ihren Familiennamen und ein komplettes Geräteset liefern.
class DeviceFamilyFactory(ABC):
    @property
    @abstractmethod
    def family_key(self) -> str: ...

    @abstractmethod
    def create_device_set(self) -> list[Device]: ...


# Die Sensor-Creators aus Phase 2 liefern Sensor Objekte
# Diese Hilfsfunktion wandelt sie in die gemeinsame Device Struktur um
def _sensor_to_device(sensor_type: str, family: str, protocol: str, display_name: str) -> Device:
    sensor = get_creator(sensor_type).create_sensor(display_name)
    return Device(
        id=None,
        device_type=sensor.device_type,
        role="sensor",
        device_family=  family,
        display_name =sensor.display_name,
        default_config={**sensor.default_config, "protocol": protocol},
    )


# Aktuatoren werden in dieser Phase direkt als Device erzeugt
# Die Konfiguration wird um das familienabhängige Protokoll ergänzt
def _actuator(device_type: str, family: str, protocol: str, display_name: str, config: dict) -> Device:
    return Device(
        id=None,
        device_type=device_type,
        role= "actuator",
        device_family=family,
        display_name= display_name,
        default_config={**config, "protocol": protocol},
    )


class SimulationDeviceFactory(DeviceFamilyFactory):
    """Erzeugt ein Geräteset für die Entwicklung und Simulation."""

    @property
    def family_key(self) -> str:
        return "simulation"

    def create_device_set(self) -> list[Device]:
        family = self.family_key
        protocol = "sim"

        # Ein Set besteht aus zwei Sensoren und zwei Aktuatoren
        return [
            _sensor_to_device("moisture", family, protocol, "Sim moisture sensor"),
            _sensor_to_device("light", family, protocol, "Sim light sensor"),
            _actuator(
                "water_pump", family, protocol, "Sim irrigation pump",
                {"flow_rate_lpm": 2.5},
            ),
            _actuator(
                "grow_light", family, protocol, "Sim grow light",
                {"max_brightness_pct": 100},
            ),
        ]


class EdgeHardwareFactory(DeviceFamilyFactory):
    """Erzeugt ein Geräteset für Edge-Hardware als Stub."""

    @property
    def family_key(self) -> str:
        return "edge"

    def create_device_set(self) -> list[Device]:
        family = self.family_key
        protocol = "gpio-stub"

        # Die Struktur entspricht der Simulation, aber Namen und Protokoll unterscheiden sich
        return [
            _sensor_to_device("moisture", family, protocol, "Edge moisture sensor"),
            _sensor_to_device("light", family, protocol, "Edge light sensor"),
            _actuator(
                "water_pump", family, protocol, "Edge irrigation pump",
                {"relay_pin": 17},
            ),
            _actuator(
                "grow_light", family, protocol, "Edge grow light",
                {"relay_pin": 27},
            ),
        ]


# Bekannte Familien werden einmalig mit ihrer Factory verknüpft.
# So muss der aufrufende Code die konkreten Factory-Klassen nicht kennen.
_FACTORIES: dict[str, DeviceFamilyFactory] = {
    "simulation": SimulationDeviceFactory(),
    "edge": EdgeHardwareFactory(),
}


def get_family_factory(family: str) -> DeviceFamilyFactory:
    """Gibt die Factory für einen Familiennamen zurück."""
    try:
        return _FACTORIES[family]
    except KeyError:
        # Ein unbekannter Name soll nicht unbemerkt zu einem falschen Geräteset führen.
        raise ValueError(f"Unknown device family: {family}")
