from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from application.locations.config_service import LocationConfigService
from domain.locations.entity import LocationConfig
from infrastructure.persistence.models import LocationRow, ZoneRow
from interfaces.api.locations import get_service
from main import app


class InMemoryLocationRepository:
    """Ersetzt die Datenbank im Test; gleiche Methoden wie LocationRepository."""

    def __init__(self):
        self._configs: dict[UUID, tuple[LocationRow, list[ZoneRow]]] = {}
        self.save_calls = 0

    def save_config(self, config: LocationConfig) -> tuple[LocationRow, list[ZoneRow]]:
        self.save_calls += 1
        # Die echte DB vergibt die ids, hier tun es UUIDs aus Python.
        location_id = uuid4()
        location_row = LocationRow(id=location_id, name=config.location.name)
        zone_rows = [
            ZoneRow(
                id=uuid4(),
                location_id=location_id,
                name=zone.name,
                moisture_threshold_low=zone.moisture_threshold_low,
                moisture_threshold_high=zone.moisture_threshold_high,
                schedule=zone.schedule,
            )
            for zone in config.location.zones
        ]
        self._configs[location_id] = (location_row, zone_rows)
        return location_row, zone_rows

    def get_config(self, location_id: UUID):
        return self._configs.get(location_id)


@pytest.fixture
def repo():
    return InMemoryLocationRepository()


@pytest.fixture
def client(repo):
    app.dependency_overrides[get_service] = lambda: LocationConfigService(repo)
    yield TestClient(app)
    app.dependency_overrides.clear()


VALID_PAYLOAD = {
    "location_name": "Lab Site A",
    "zones": [
        {
            "name": "Bench 1",
            "moisture_threshold_low": 0.2,
            "moisture_threshold_high": 0.45,
            "schedule": {"watering": "08:00"},
        }
    ],
}


def test_create_config_returns_201_with_location_and_zones(client):
    response = client.post("/api/locations/config", json=VALID_PAYLOAD)
    assert response.status_code == 201

    body = response.json()
    assert body["location"]["name"] == "Lab Site A"
    assert len(body["zones"]) == 1
    zone = body["zones"][0]
    # Jede Zone kennt ihren Standort - und zwar unter location_id.
    assert zone["location_id"] == body["location"]["id"]
    assert zone["moisture_threshold_low"] == 0.2
    assert zone["schedule"] == {"watering": "08:00"}


def test_get_config_returns_saved_structure(client):
    created = client.post("/api/locations/config", json=VALID_PAYLOAD).json()
    location_id = created["location"]["id"]

    response = client.get(f"/api/locations/{location_id}/config")
    assert response.status_code == 200

    body = response.json()
    assert body["location"]["id"] == location_id
    assert all(zone["location_id"] == location_id for zone in body["zones"])


def test_unknown_location_returns_404(client):
    response = client.get(f"/api/locations/{uuid4()}/config")
    assert response.status_code == 404


def test_invalid_thresholds_return_400_and_do_not_save(client, repo):
    payload = {
        "location_name": "Lab Site A",
        "zones": [
            {"name": "Bench 1", "moisture_threshold_low": 0.6, "moisture_threshold_high": 0.3}
        ],
    }
    response = client.post("/api/locations/config", json=payload)
    assert response.status_code == 400
    assert "low" in response.json()["detail"]
    # Der Builder bricht ab, bevor das Repository ueberhaupt gefragt wird.
    assert repo.save_calls == 0


def test_missing_zones_return_400(client, repo):
    response = client.post(
        "/api/locations/config", json={"location_name": "Lab Site A", "zones": []}
    )
    assert response.status_code == 400
    assert repo.save_calls == 0


def test_missing_location_name_returns_400(client, repo):
    response = client.post("/api/locations/config", json={"location_name": "", "zones": []})
    assert response.status_code == 400
    assert repo.save_calls == 0
