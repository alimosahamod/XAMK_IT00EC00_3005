from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from application.devices.family_service import DeviceFamilyService
from domain.devices.entity import Device
from interfaces.api.devices import get_service
from main import app


class InMemoryDeviceRepository:
    """Ersetzt die Datenbank im Test; gleiche Methoden wie DeviceRepository."""

    def __init__(self):
        self._devices: list[Device] = []

    def save_devices(self, devices: list[Device]) -> list[Device]:
        # Die echte DB vergibt die id, hier tut es eine UUID aus Python.
        saved = [replace(device, id=uuid4()) for device in devices]
        self._devices.extend(saved)
        return saved

    def list_devices(self, *, device_family=None, role=None) -> list[Device]:
        return [
            d
            for d in self._devices
            if (device_family is None or d.device_family == device_family)
            and (role is None or d.role == role)
        ]


@pytest.fixture
def client():
    repo = InMemoryDeviceRepository()
    app.dependency_overrides[get_service] = lambda: DeviceFamilyService(repo)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_provision_returns_201_and_four_devices(client):
    response = client.post("/api/devices/provision?family=simulation")
    assert response.status_code == 201
    body = response.json()
    assert len(body) == 4
    assert {d["device_family"] for d in body} == {"simulation"}


def test_unknown_family_returns_400(client):
    response = client.post("/api/devices/provision?family=cloud")
    assert response.status_code == 400


def test_family_filter_returns_only_that_family(client):
    client.post("/api/devices/provision?family=simulation")
    client.post("/api/devices/provision?family=edge")

    edge = client.get("/api/devices?family=edge").json()
    assert len(edge) == 4
    assert {d["device_family"] for d in edge} == {"edge"}
    # Die Liste enthaelt auch Aktuatoren, nicht nur Sensoren.
    assert any(d["role"] == "actuator" for d in edge)


def test_role_filter_returns_only_actuators(client):
    client.post("/api/devices/provision?family=simulation")

    actuators = client.get("/api/devices?family=simulation&role=actuator").json()
    assert len(actuators) == 2
    assert {d["role"] for d in actuators} == {"actuator"}
