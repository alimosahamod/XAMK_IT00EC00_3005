from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from infrastructure.db import engine, get_db
from main import app
from test_automation_api import seed_reading, setup_location_with_reading

# Integrationstest gegen die geseedete Postgres-DB: ein GET liefert die ganze Uebersicht.
# Alles laeuft in einer Transaktion, die am Ende zurueckrollt.


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


def test_overview_returns_strategy_and_readings(client, db):
    location = setup_location_with_reading(client, db, moisture=0.30)
    client.put(f"/api/locations/{location.id}/automation", json={"strategy_key": "aggressive"})

    response = client.get(f"/api/locations/{location.id}/overview")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "location",
        "device_counts",
        "latest_readings",
        "strategy_key",
        "last_recommendation",
    }
    assert body["location"] == {"id": str(location.id), "name": "Test location"}
    assert body["device_counts"] == {"sensor": 1, "actuator": 0}
    assert body["latest_readings"][0]["value"] == 0.30
    assert body["strategy_key"] == "aggressive"
    assert body["last_recommendation"]["action"] == "irrigate"


def test_overview_reflects_new_reading_and_strategy(client, db):
    location = setup_location_with_reading(client, db, moisture=0.30)
    url = f"/api/locations/{location.id}/overview"
    client.put(f"/api/locations/{location.id}/automation", json={"strategy_key": "conservative"})
    sensor_id = client.get(url).json()["latest_readings"][0]["device_id"]

    seed_reading(db, sensor_id, 0.10)
    body = client.get(url).json()

    assert len(body["latest_readings"]) == 1
    assert body["latest_readings"][0]["value"] == 0.10
    assert body["last_recommendation"]["action"] == "irrigate"


def test_overview_without_strategy_has_no_recommendation(client, db):
    location = setup_location_with_reading(client, db)

    body = client.get(f"/api/locations/{location.id}/overview").json()

    assert body["strategy_key"] is None
    assert body["last_recommendation"] is None


def test_overview_missing_location_returns_404(client):
    assert client.get(f"/api/locations/{uuid4()}/overview").status_code == 404
