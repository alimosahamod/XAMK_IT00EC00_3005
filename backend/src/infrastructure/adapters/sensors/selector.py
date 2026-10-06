from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from infrastructure.adapters.sensors.vendor_stub import VendorStubSensorAdapter

# Auswahlregel: die Geraetefamilie aus Phase 3 bestimmt den Adapter.
#   simulation -> SimulationSensorAdapter (source="simulation")
#   edge       -> VendorStubSensorAdapter (source="vendor")
# Ein dritter Vendor ist nur ein neuer Eintrag hier, kein Umbau im Service.
_ADAPTERS: dict[str, SensorPort] = {
    "simulation": SimulationSensorAdapter(),
    "edge": VendorStubSensorAdapter(),
}


def select_sensor_adapter(device: Device) -> SensorPort:
    """Die einzige Stelle, die konkrete Adapter-Klassen kennt."""
    if device.role != "sensor":
        raise SensorReadError(f"Device {device.id} is not a sensor")
    try:
        return _ADAPTERS[device.device_family]
    except KeyError:
        raise SensorReadError(f"No sensor adapter for family: {device.device_family}")
