from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from infrastructure.db import engine, get_db
from infrastructure.persistence.models import ActuatorExecutionLogRow, ActuatorStateRow
from main import app

# Integrationstest gegen die echte Postgres-DB: der echte Decorator-Stapel aus
# build_actuator() schreibt in actuator_execution_log. Alles wird am Ende zurueckgerollt.
# Seit Phase 10 erreicht man den Stapel nur noch ueber POST /api/commands.


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


def new_actuator(client) -> dict:
    devices = client.post("/api/devices/provision?family=simulation").json()
    return next(d for d in devices if d["role"] == "actuator")


def force_running_for(db, device_id, duration: timedelta) -> None:
    # Demo-Trick: der Aktuator laeuft "schon seit" duration (updated_at aus Phase 8).
    row = db.get(ActuatorStateRow, device_id)
    row.state = "running"
    row.updated_at = datetime.now(UTC) - duration
    db.commit()


def log_rows(db, device_id) -> list[ActuatorExecutionLogRow]:
    db.expire_all()
    return list(db.scalars(select(ActuatorExecutionLogRow).where(ActuatorExecutionLogRow.device_id == device_id)))


def send(client, device_id, command_type: str):
    return client.post("/api/commands", json={"command_type": command_type, "device_id": device_id})


def test_allowed_apply_inserts_success_row(client, db):
    actuator = new_actuator(client)

    response = send(client, actuator["id"], "start_pump")

    assert response.json()["status"] == "success"
    rows = log_rows(db, actuator["id"])
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].policy_applied == ["maxRunTime", "logging"]
    assert rows[0].message is None


def test_blocked_apply_inserts_failed_row_and_is_listed(client, db):
    actuator = new_actuator(client)
    force_running_for(db, actuator["id"], timedelta(hours=2))

    # stop ist im Zustand running erlaubt -> der Befehl erreicht den Decorator, der blockiert.
    response = send(client, actuator["id"], "stop_pump")

    assert response.json()["status"] == "failed"
    assert response.json()["error_message"] == "Max run time exceeded"
    # Die Zeile steht in der Tabelle, obwohl der Befehl blockiert wurde.
    rows = log_rows(db, actuator["id"])
    assert [(r.success, r.policy_applied, r.message) for r in rows] == [
        (False, ["maxRunTime", "logging"], "Max run time exceeded")
    ]
    # Und das Dashboard sieht sie ueber den GET-Endpunkt.
    listed = client.get("/api/actuators/executions?limit=20").json()
    entry = next(e for e in listed if e["device_id"] == actuator["id"])
    assert entry["success"] is False
    assert entry["policy_applied"] == ["maxRunTime", "logging"]
    assert entry["message"] == "Max run time exceeded"


def test_executions_are_newest_first_and_limited(client, db):
    actuator = new_actuator(client)
    for command_type in ("start_pump", "stop_pump", "start_pump"):
        send(client, actuator["id"], command_type)

    listed = client.get("/api/actuators/executions?limit=2").json()

    assert len(listed) == 2
    assert listed[0]["created_at"] >= listed[1]["created_at"]


def test_unknown_device_returns_404_without_log_row(client, db):
    before = db.scalar(select(func.count()).select_from(ActuatorExecutionLogRow))

    response = send(client, str(uuid4()), "start_pump")

    assert response.status_code == 404
    assert db.scalar(select(func.count()).select_from(ActuatorExecutionLogRow)) == before
