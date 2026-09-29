import pytest

from domain.devices.family_factory import (
    EdgeHardwareFactory,
    SimulationDeviceFactory,
    get_family_factory,
)


def test_simulation_factory_returns_four_devices():
    devices = SimulationDeviceFactory().create_device_set()
    assert len(devices) == 4
    # Ein Set gehoert zu genau einer Familie.
    assert {d.device_family for d in devices} == {"simulation"}
    # Sensoren und Aktuatoren kommen zusammen, zwei von jeder Rolle.
    assert [d.role for d in devices].count("sensor") == 2
    assert [d.role for d in devices].count("actuator") == 2


def test_edge_factory_differs_from_simulation():
    sim = SimulationDeviceFactory().create_device_set()
    edge = EdgeHardwareFactory().create_device_set()

    assert {d.device_family for d in edge} == {"edge"}
    # Gleiche Geraetetypen, aber andere Konfiguration und andere Labels.
    assert [d.device_type for d in sim] == [d.device_type for d in edge]
    assert sim[0].default_config["protocol"] != edge[0].default_config["protocol"]
    assert sim[0].display_name != edge[0].display_name


def test_factory_lookup_by_family_key():
    assert get_family_factory("simulation").family_key == "simulation"
    assert get_family_factory("edge").family_key == "edge"


def test_unknown_family_raises():
    with pytest.raises(ValueError):
        get_family_factory("cloud")


def test_sensors_are_built_by_phase_two_creators():
    devices = SimulationDeviceFactory().create_device_set()
    sensors = [d for d in devices if d.role == "sensor"]
    # Die Creator-Defaults aus Phase 2 bleiben erhalten, die Familie kommt dazu.
    moisture = next(d for d in sensors if d.device_type == "moisture_sensor")
    assert moisture.default_config["moisture_threshold"] == 30
    assert next(d for d in sensors if d.device_type == "light_sensor").default_config["unit"] == "lux"
