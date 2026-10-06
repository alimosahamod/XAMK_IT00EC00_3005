import random
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.adapters.sensors.selector import select_sensor_adapter
from infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from infrastructure.adapters.sensors.vendor_stub import (
    VendorStubSensorAdapter,
    translate_vendor_payload,
)

FIXED_TIME = datetime(2026, 8, 28, 9, 0, tzinfo=UTC)


def make_device(device_type="moisture_sensor", family="simulation", role="sensor") -> Device:
    return Device(
        id=uuid4(),
        device_type=device_type,
        role=role,
        device_family=family,
        display_name="Test",
        default_config={},
    )


def test_vendor_adapter_normalizes_raw_payload():
    device_id = UUID("11111111-1111-1111-1111-111111111111")
    raw = {
        "sensorRef": str(device_id),
        "ch": "SOIL_MOIST",
        "val": 31.5,
        "uom": "PCT",
        "tsMillis": int(FIXED_TIME.timestamp() * 1000),
        "status": "OK",
    }

    reading = translate_vendor_payload(raw)

    # Prozent wird zu Anteil, Epoch-ms wird zu datetime mit Zeitzone.
    assert reading.device_id == device_id
    assert reading.value == pytest.approx(0.315)
    assert reading.unit == "vwc"
    assert reading.source == "vendor"
    assert reading.recorded_at == FIXED_TIME


def test_vendor_adapter_converts_kilolux_to_lux():
    raw = {"sensorRef": str(uuid4()), "val": 12.4, "uom": "KLX", "tsMillis": 0, "status": "OK"}
    reading = translate_vendor_payload(raw)
    assert reading.unit == "lux"
    assert reading.value == pytest.approx(12400)


def test_vendor_error_status_raises():
    with pytest.raises(SensorReadError):
        translate_vendor_payload({"sensorRef": str(uuid4()), "status": "E_NO_CHANNEL"})


def test_simulation_adapter_returns_plausible_moisture():
    adapter = SimulationSensorAdapter(rng=random.Random(1), clock=lambda: FIXED_TIME)
    device = make_device("moisture_sensor")

    reading = adapter.read(device)

    assert reading.device_id == device.id
    assert reading.unit == "vwc"
    assert 0.15 <= reading.value <= 0.45
    assert reading.source == "simulation"
    assert reading.recorded_at == FIXED_TIME


def test_same_logical_read_gives_different_sources():
    sim = SimulationSensorAdapter().read(make_device("light_sensor"))
    vendor = VendorStubSensorAdapter().read(make_device("light_sensor", family="edge"))
    # Gleiche Form, gleiche Einheit - nur die Quelle unterscheidet sich.
    assert (sim.unit, vendor.unit) == ("lux", "lux")
    assert (sim.source, vendor.source) == ("simulation", "vendor")


def test_selector_picks_adapter_by_family():
    assert isinstance(select_sensor_adapter(make_device(family="simulation")), SimulationSensorAdapter)
    assert isinstance(select_sensor_adapter(make_device(family="edge")), VendorStubSensorAdapter)


def test_selector_rejects_actuator_and_unknown_family():
    with pytest.raises(SensorReadError):
        select_sensor_adapter(make_device("water_pump", role="actuator"))
    with pytest.raises(SensorReadError):
        select_sensor_adapter(make_device(family="cloud"))


def test_simulation_actuator_records_command():
    actuator = SimulationActuatorAdapter()
    device_id = uuid4()

    actuator.apply(device_id, "on", {"duration_s": 30})

    assert len(actuator.applied) == 1
    assert actuator.applied[0].device_id == device_id
    assert actuator.applied[0].command == "on"
    assert actuator.applied[0].payload == {"duration_s": 30}
