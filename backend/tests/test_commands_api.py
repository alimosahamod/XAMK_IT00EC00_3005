from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from infrastructure.db import engine, get_db
from infrastructure.persistence.models import (
    ActuatorExecutionLogRow,
    ActuatorStateRow,
    CommandLogRow,
)
from main import app

# API-Tests fuer POST/GET /api/commands gegen die echte Postgres-DB.
# Alles laeuft in einer Transaktion und wird am Ende zurueckgerollt.


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


def new_actuator(client, device_type: str = "water_pump") -> dict:
    devices = client.post("/api/devices/provision?family=simulation").json()
    return next(d for d in devices if d["device_type"] == device_type)


def send(client, device_id: str, command_type: str, payload: dict | None = None):
    body = {"command_type": command_type, "device_id": device_id, "payload": payload or {}}
    return client.post("/api/commands", json=body)


def set_state(db, device_id: str, state: str, since: timedelta = timedelta(0)) -> None:
    row = db.get(ActuatorStateRow, device_id)
    row.state = state
    row.updated_at = datetime.now(UTC) - since
    db.commit()


def stored_state(db, device_id: str) -> str:
    db.expire_all()
    return db.get(ActuatorStateRow, device_id).state


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_start_pump_returns_success_and_device_shows_running(client, db):
    pump = new_actuator(client)

    response = send(client, pump["id"], "start_pump")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["error_message"] is None
    assert stored_state(db, pump["id"]) == "running"
    # Das UI sieht ueber allowed_commands, dass jetzt "stop" moeglich ist.
    device = next(d for d in client.get("/api/devices?role=actuator").json() if d["id"] == pump["id"])
    assert device["state"] == "running"
    assert "stop" in device["allowed_commands"]


def test_rejected_command_is_200_with_status_and_appears_in_history(client, db):
    pump = new_actuator(client)
    set_state(db, pump["id"], "maintenance")

    response = send(client, pump["id"], "start_pump")

    # Entscheidung: rejected kommt als 200 mit status=rejected, nicht als 409.
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert stored_state(db, pump["id"]) == "maintenance"
    history = client.get("/api/commands?limit=50").json()
    entry = next(e for e in history if e["device_id"] == pump["id"])
    assert (entry["command_type"], entry["status"]) == ("start_pump", "rejected")


def test_policy_block_is_failed_in_command_log_and_execution_log(client, db):
    pump = new_actuator(client)
    set_state(db, pump["id"], "running", since=timedelta(hours=2))
    executions_before = count(db, ActuatorExecutionLogRow)

    response = send(client, pump["id"], "stop_pump")

    assert response.json()["status"] == "failed"
    assert response.json()["error_message"] == "Max run time exceeded"
    assert stored_state(db, pump["id"]) == "running"  # kein Zustandswechsel nach failed
    # Beide Logs sehen den Fehlschlag: command_log (Absicht) und execution_log (Decorator).
    assert count(db, ActuatorExecutionLogRow) == executions_before + 1


def test_set_light_level_passes_payload_through(client, db):
    light = new_actuator(client, "grow_light")

    response = send(client, light["id"], "set_light_level", {"level": 70})

    assert response.json()["status"] == "success"
    assert response.json()["payload"] == {"level": 70}
    assert stored_state(db, light["id"]) == "running"


@pytest.mark.parametrize(
    ("command_type", "payload"),
    [("fly_to_moon", {}), ("set_light_level", {"level": 500})],
)
def test_unknown_type_or_bad_payload_is_400_without_log_row(client, db, command_type, payload):
    pump = new_actuator(client)
    before = count(db, CommandLogRow)

    response = send(client, pump["id"], command_type, payload)

    assert response.status_code == 400
    assert count(db, CommandLogRow) == before


def test_unknown_device_is_404_without_log_row(client, db):
    before = count(db, CommandLogRow)

    response = send(client, str(uuid4()), "start_pump")

    assert response.status_code == 404
    assert count(db, CommandLogRow) == before


def test_history_is_newest_first_and_limited(client, db):
    pump = new_actuator(client)
    for command_type in ("start_pump", "stop_pump", "start_pump"):
        send(client, pump["id"], command_type)

    history = client.get("/api/commands?limit=2").json()

    assert len(history) == 2
    assert history[0]["created_at"] >= history[1]["created_at"]
