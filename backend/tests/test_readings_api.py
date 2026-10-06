from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from domain.devices.entity import Device
from infrastructure.db import engine, get_db
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.models import ReadingRow
from main import app

# Diese Tests laufen gegen die echte Postgres-DB (docker compose up postgres).
# Alles passiert in einer aeusseren Transaktion, die am Ende zurueckgerollt
# wird - die commits im Repository werden dabei zu Savepoints.


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


def save_device(db, family="simulation", role="sensor", device_type="moisture_sensor") -> Device:
    return DeviceRepository(db).save_device(
        Device(
            id=None,
            device_type=device_type,
            role=role,
            device_family=family,
            display_name="Test sensor",
            default_config={},
        )
    )


def count_readings(db, device_id) -> int:
    stmt = select(func.count()).select_from(ReadingRow).where(ReadingRow.device_id == device_id)
    return db.execute(stmt).scalar_one()


def test_read_inserts_sensor_reading(client, db):
    device = save_device(db)

    first = client.post(f"/api/sensors/{device.id}/read")
    client.post(f"/api/sensors/{device.id}/read")

    assert first.status_code == 201
    body = first.json()
    assert body["device_id"] == str(device.id)
    assert body["unit"] == "vwc"
    assert body["source"] == "simulation"
    # Zwei Lesevorgaenge -> zwei Zeilen: Historie statt Ueberschreiben.
    assert count_readings(db, device.id) == 2


def test_edge_device_is_read_by_vendor_adapter(client, db):
    device = save_device(db, family="edge", device_type="light_sensor")
    body = client.post(f"/api/sensors/{device.id}/read").json()
    assert body["source"] == "vendor"
    assert body["unit"] == "lux"


def test_latest_reading_comes_from_db(client, db):
    device = save_device(db)
    client.post(f"/api/sensors/{device.id}/read")
    latest = client.post(f"/api/sensors/{device.id}/read").json()

    response = client.get(f"/api/sensors/{device.id}/readings?limit=1")

    assert response.status_code == 200
    assert response.json() == [latest]


def test_missing_device_returns_404(client):
    assert client.post(f"/api/sensors/{uuid4()}/read").status_code == 404
    assert client.get(f"/api/sensors/{uuid4()}/readings").status_code == 404


def test_reading_an_actuator_returns_400(client, db):
    device = save_device(db, role="actuator", device_type="water_pump")
    response = client.post(f"/api/sensors/{device.id}/read")
    assert response.status_code == 400
    assert count_readings(db, device.id) == 0
