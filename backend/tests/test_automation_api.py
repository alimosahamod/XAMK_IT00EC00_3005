from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from domain.devices.entity import Device
from domain.sensors.reading import Reading
from infrastructure.db import engine, get_db
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.models import LocationRow, ZoneRow
from infrastructure.persistence.reading_repository import ReadingRepository
from main import app

# Integrationstest gegen die echte Postgres-DB mit geseedeten Zonen und
# Messwerten. Alles laeuft in einer Transaktion, die am Ende zurueckrollt.


@pytest.fixture
def db():
    try:
        connection = engine.connect()
    except OperationalError:
        pytest.skip("Postgres is not reachable")
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def save_location(db, low=0.25, high=0.45) -> LocationRow:
    location = LocationRow(name="Test location")
    db.add(location)
    db.flush()
    db.add(
        ZoneRow(
            location_id=location.id,
            name="Bench 1",
            moisture_threshold_low=low,
            moisture_threshold_high=high,
        )
    )
    db.commit()
    return location


def save_sensor(db, device_type="moisture_sensor") -> Device:
    return DeviceRepository(db).save_device(
        Device(
            id=None,
            device_type=device_type,
            role="sensor",
            device_family="simulation",
            display_name="Test sensor",
            default_config={},
        )
    )


def seed_reading(db, device_id, value: float) -> None:
    ReadingRepository(db).insert(
        Reading(
            device_id=device_id,
            value=value,
            unit="vwc",
            source="simulation",
            recorded_at=datetime.now(UTC),
        )
    )


def setup_location_with_reading(client, db, moisture=0.30) -> LocationRow:
    location = save_location(db)
    sensor = save_sensor(db)
    assert client.put(f"/api/locations/{location.id}/sensors/{sensor.id}").status_code == 204
    seed_reading(db, sensor.id, moisture)
    return location


def test_put_saves_strategy(client, db):
    location = save_location(db)

    response = client.put(
        f"/api/locations/{location.id}/automation", json={"strategy_key": "aggressive"}
    )

    assert response.status_code == 200
    assert client.get(f"/api/locations/{location.id}/automation").json() == {
        "location_id": str(location.id),
        "strategy_key": "aggressive",
    }


def test_evaluate_after_switch_differs(client, db):
    location = setup_location_with_reading(client, db, moisture=0.30)
    url = f"/api/locations/{location.id}/automation"

    client.put(url, json={"strategy_key": "conservative"})
    first = client.post(f"{url}/evaluate").json()
    client.put(url, json={"strategy_key": "aggressive"})
    second = client.post(f"{url}/evaluate").json()

    assert first["strategy_key"] == "conservative"
    assert first["action"] == "wait"
    assert second["strategy_key"] == "aggressive"
    assert second["action"] == "irrigate"


def test_unknown_key_returns_400(client, db):
    location = save_location(db)

    response = client.put(
        f"/api/locations/{location.id}/automation", json={"strategy_key": "random"}
    )

    assert response.status_code == 400


def test_missing_location_returns_404(client):
    assert client.post(f"/api/locations/{uuid4()}/automation/evaluate").status_code == 404
    response = client.put(
        f"/api/locations/{uuid4()}/automation", json={"strategy_key": "conservative"}
    )
    assert response.status_code == 404


def test_unassigned_sensor_is_ignored(client, db):
    # Der Sensor hat Messwerte, gehoert aber zu keinem Standort.
    location = save_location(db)
    sensor = save_sensor(db)
    seed_reading(db, sensor.id, 0.10)
    client.put(f"/api/locations/{location.id}/automation", json={"strategy_key": "conservative"})

    response = client.post(f"/api/locations/{location.id}/automation/evaluate")

    assert response.status_code == 409


def test_link_light_sensor_returns_400(client, db):
    location = save_location(db)
    sensor = save_sensor(db, device_type="light_sensor")

    response = client.put(f"/api/locations/{location.id}/sensors/{sensor.id}")

    assert response.status_code == 400
