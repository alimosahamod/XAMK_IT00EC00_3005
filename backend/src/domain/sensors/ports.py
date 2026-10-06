from abc import ABC, abstractmethod

from domain.devices.entity import Device
from domain.sensors.reading import Reading


class SensorPort(ABC):
    """Target-Schnittstelle (Port) fuer alle Sensor-Quellen.

    Die Anwendung kennt nur diesen Port. Wie ein Wert wirklich gelesen wird
    (Simulation, Vendor-API, spaeter GPIO), steckt in den Adaptern in
    `infrastructure/adapters/sensors/`.
    """

    @abstractmethod
    def read(self, device: Device) -> Reading:
        """Liest einen Wert und gibt ihn normalisiert zurueck.

        Wirft SensorReadError, wenn kein gueltiger Wert moeglich ist.
        """
