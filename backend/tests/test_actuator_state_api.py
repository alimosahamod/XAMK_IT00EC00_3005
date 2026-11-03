from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from infrastructure.db import engine, get_db
from infrastructure.persistence.models import ActuatorStateRow
from main import app

# Integrationstest gegen die echte Postgres-DB. Alles laeuft in einer
# Transaktion, die am Ende zurueckgerollt wird (wie test_automation_api.py).


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


def provision(client) -> list[dict]:
    return client.post("/api/devices/provision?family=simulation").json()


def first_actuator(devices: list[dict]) -> dict:
    return next(d for d in devices if d["role"] == "actuator")


def stored_state(db, device_id) -> str:
    # Frisch aus der DB lesen, nicht aus dem Session-Cache.
    db.expire_all()
    return db.get(ActuatorStateRow, device_id).state


def test_new_actuators_start_idle_with_commands(client):
    devices = provision(client)

    actuators = [d for d in devices if d["role"] == "actuator"]
    sensors = [d for d in devices if d["role"] == "sensor"]
    assert {a["state"] for a in actuators} == {"idle"}
    assert "start" in actuators[0]["allowed_commands"]
    # Sensoren haben keinen Lebenszyklus.
    assert all(s["state"] is None and s["allowed_commands"] == [] for s in sensors)


def test_legal_transition_updates_row(client, db):
    actuator = first_actuator(provision(client))

    response = client.post(
        f"/api/devices/{actuator['id']}/transition", json={"target": "running"}
    )

    assert response.status_code == 200
    assert response.json()["state"] == "running"
    assert response.json()["allowed_commands"] == ["stop", "report_fault"]
    assert stored_state(db, actuator["id"]) == "running"
    # Auch die Liste liest den neuen Zustand aus der DB.
    listed = client.get("/api/devices?role=actuator").json()
    assert next(d for d in listed if d["id"] == actuator["id"])["state"] == "running"


def test_illegal_transition_does_not_update_row(client, db):
    actuator = first_actuator(provision(client))
    client.post(f"/api/devices/{actuator['id']}/transition", json={"target": "running"})

    response = client.post(
        f"/api/devices/{actuator['id']}/transition", json={"target": "maintenance"}
    )

    assert response.status_code == 409
    assert "running -> maintenance" in response.json()["detail"]
    assert stored_state(db, actuator["id"]) == "running"


def test_unknown_device_returns_404(client):
    response = client.post(f"/api/devices/{uuid4()}/transition", json={"target": "running"})
    assert response.status_code == 404


def test_sensor_has_no_state_and_returns_404(client):
    sensor = next(d for d in provision(client) if d["role"] == "sensor")
    response = client.post(f"/api/devices/{sensor['id']}/transition", json={"target": "running"})
    assert response.status_code == 404
