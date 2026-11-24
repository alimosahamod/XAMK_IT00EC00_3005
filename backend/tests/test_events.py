from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from application.commands.service import CommandService
from application.readings.service import ReadingService
from domain.actuators.errors import PolicyViolationError
from domain.commands.invoker import CommandInvoker
from domain.events.bus import EventBus
from domain.events.events import ReadingCreated
from domain.sensors.reading import Reading
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.db import engine, get_db
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.command_log_repository import CommandLogRepository
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.models import (
    ActuatorStateRow,
    AlertRow,
    DeviceRow,
    LocationRow,
    ReadingRow,
    ZoneRow,
)
from infrastructure.persistence.reading_repository import ReadingRepository
from interfaces.api.event_bus import build_event_bus, get_event_bus
from main import app

# --- Teil 1: EventBus ohne DB ----------------------------------------------


def test_bus_calls_handlers_in_subscription_order():
    bus = EventBus()
    calls = []
    bus.subscribe(str, lambda e: calls.append(("first", e)))
    bus.subscribe(str, lambda e: calls.append(("second", e)))
    bus.subscribe(int, lambda e: calls.append(("int", e)))

    bus.publish("hello")

    # Nur Handler der passenden Klasse, in Anmelde-Reihenfolge.
    assert calls == [("first", "hello"), ("second", "hello")]


def test_failing_handler_does_not_stop_the_others():
    bus = EventBus()
    calls = []

    def broken(event):
        raise RuntimeError("boom")

    bus.subscribe(str, broken)
    bus.subscribe(str, calls.append)

    bus.publish("x")  # wirft nicht

    assert calls == ["x"]


# --- Teil 2: gegen die echte Postgres-DB (Transaktion wird zurueckgerollt) --


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


class RecordingBus:
    """Merkt sich, was die Services publizieren, und reicht es an den echten Bus weiter."""

    def __init__(self, inner: EventBus):
        self.inner = inner
        self.published = []

    def publish(self, event):
        self.published.append(event)
        self.inner.publish(event)


@pytest.fixture
def spy_bus(db):
    # Echte Verdrahtung aus der Composition Root, nur mit "Mitschnitt" davor.
    return RecordingBus(build_event_bus(db))


@pytest.fixture
def client(db, spy_bus):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_event_bus] = lambda: spy_bus
    yield TestClient(app)
    app.dependency_overrides.clear()


def bench_1(db) -> ZoneRow:
    location = LocationRow(name="Test greenhouse")
    db.add(location)
    db.flush()
    zone = ZoneRow(
        location_id=location.id,
        name="Bench 1",
        moisture_threshold_low=0.20,
        moisture_threshold_high=0.45,
    )
    db.add(zone)
    db.commit()
    return zone


def new_device(db, role="sensor", device_type="moisture_sensor", zone=None, tracking=True) -> DeviceRow:
    row = DeviceRow(
        device_type=device_type,
        role=role,
        display_name="Test device",
        location_id=zone.location_id if zone else None,
        zone_id=zone.id if zone else None,
        tracking_enabled=tracking,
    )
    db.add(row)
    db.flush()
    if role == "actuator":
        db.add(ActuatorStateRow(device_id=row.id, state="idle"))
    db.commit()
    return row


def alerts_for(db, device_id) -> list[AlertRow]:
    db.expire_all()
    return list(db.scalars(select(AlertRow).where(AlertRow.device_id == device_id)))


class FixedSensor:
    """Sensor-Port mit festem Wert, damit die Schwellwert-Regel testbar ist."""

    def __init__(self, value: float):
        self.value = value

    def read(self, device):
        return Reading(device.id, self.value, "vwc", "simulation", datetime.now(UTC))


def ingest(db, device_id, value: float) -> None:
    service = ReadingService(
        DeviceRepository(db), ReadingRepository(db), lambda d: FixedSensor(value), build_event_bus(db)
    )
    service.take_reading(device_id)


# Ingest: reading.created nur bei tracking_enabled


def test_read_on_tracked_device_publishes_reading_created(client, db, spy_bus):
    zone = bench_1(db)
    device = new_device(db, zone=zone)

    assert client.post(f"/api/sensors/{device.id}/read").status_code == 201

    events = [e for e in spy_bus.published if isinstance(e, ReadingCreated)]
    assert len(events) == 1
    assert events[0].device_id == device.id
    assert events[0].unit == "vwc"
    assert events[0].source == "simulation"
    # Vom Geraet kopiert.
    assert (events[0].location_id, events[0].zone_id) == (zone.location_id, zone.id)


def test_read_with_tracking_off_stores_row_but_does_not_publish(client, db, spy_bus):
    device = new_device(db, tracking=False)

    assert client.post(f"/api/sensors/{device.id}/read").status_code == 201

    stored = db.scalar(select(func.count()).select_from(ReadingRow).where(ReadingRow.device_id == device.id))
    assert stored == 1
    assert spy_bus.published == []


def test_unassigned_device_publishes_null_ids(client, db, spy_bus):
    device = new_device(db)

    client.post(f"/api/sensors/{device.id}/read")

    (event,) = spy_bus.published
    assert (event.location_id, event.zone_id) == (None, None)


# MoistureThresholdSubscriber -> AlertPersistenceSubscriber


def test_low_moisture_on_bench_1_inserts_threshold_alert(db):
    zone = bench_1(db)
    device = new_device(db, zone=zone)

    ingest(db, device.id, 0.10)  # strikt unter low=0.20

    (alert,) = alerts_for(db, device.id)
    assert alert.event_type == "threshold.crossed"
    assert alert.severity == "warning"
    assert alert.message == "Moisture below zone low"
    assert alert.status == "active"
    assert (alert.location_id, alert.zone_id) == (zone.location_id, zone.id)


def test_value_at_threshold_or_without_zone_inserts_nothing(db):
    zone = bench_1(db)
    at_low = new_device(db, zone=zone)
    no_zone = new_device(db)

    ingest(db, at_low.id, 0.20)  # gleich low -> nicht "strikt unter"
    ingest(db, no_zone.id, 0.10)  # keine Zone -> kein Threshold-Event

    assert alerts_for(db, at_low.id) == []
    assert alerts_for(db, no_zone.id) == []


# CommandService -> command.failed / state.changed


class MaxRunTimePort(SimulationActuatorAdapter):
    def apply(self, device_id, command, payload):
        raise PolicyViolationError("maxRunTime", "Max run time exceeded")


def test_failed_command_on_unassigned_pump_inserts_alert_with_null_ids(db):
    pump = new_device(db, role="actuator", device_type="water_pump")
    states = ActuatorStateRepository(db)
    states.save_state(pump.id, "running")
    log = CommandLogRepository(db)
    service = CommandService(
        DeviceRepository(db), states, MaxRunTimePort(), CommandInvoker(log), log, build_event_bus(db)
    )

    result = service.submit("stop_pump", pump.id)

    assert result.status == "failed"
    (alert,) = alerts_for(db, pump.id)
    assert alert.event_type == "command.failed"
    assert alert.severity == "warning"
    assert alert.message == "Max run time exceeded"
    assert (alert.location_id, alert.zone_id) == (None, None)


# ActuatorStateService -> state.changed nur fuer "error"


def test_transition_to_error_inserts_critical_alert(client, db):
    pump = new_device(db, role="actuator", device_type="water_pump")

    assert client.post(f"/api/devices/{pump.id}/transition", json={"target": "error"}).status_code == 200

    (alert,) = alerts_for(db, pump.id)
    assert alert.event_type == "state.changed"
    assert alert.severity == "critical"
    assert alert.message == "Actuator entered error"


def test_transition_to_running_publishes_but_inserts_no_alert(client, db, spy_bus):
    pump = new_device(db, role="actuator", device_type="water_pump")

    client.post(f"/api/devices/{pump.id}/transition", json={"target": "running"})

    assert [e.state for e in spy_bus.published] == ["running"]
    assert alerts_for(db, pump.id) == []


# Entkopplung: Publisher kennen die Alarm-Persistenz nicht


@pytest.mark.parametrize(
    "path",
    [
        "application/readings/service.py",
        "application/commands/service.py",
        "application/devices/state_service.py",
    ],
)
def test_publishers_do_not_import_alert_persistence(path):
    source = (Path(__file__).parent.parent / "src" / path).read_text()
    assert "AlertRepository" not in source
    assert "AlertRow" not in source


# --- Teil 3: GET /api/alerts --------------------------------------------------


def second_zone(db, zone: ZoneRow) -> ZoneRow:
    other = ZoneRow(
        location_id=zone.location_id, name="Bench 2", moisture_threshold_low=0.20, moisture_threshold_high=0.45
    )
    db.add(other)
    db.commit()
    return other


def test_bench_1_alert_is_returned_only_for_its_zone(client, db):
    zone = bench_1(db)
    other = second_zone(db, zone)
    device = new_device(db, zone=zone)

    ingest(db, device.id, 0.10)

    response = client.get(f"/api/alerts?zone_id={zone.id}")
    assert response.status_code == 200
    (alert,) = response.json()
    assert alert["event_type"] == "threshold.crossed"
    assert alert["zone_id"] == str(zone.id)
    assert alert["location_id"] == str(zone.location_id)
    # acknowledged_at ist eine Spalte, aber nicht Teil der Antwort.
    assert set(alert) == {
        "id", "location_id", "zone_id", "device_id", "severity", "message", "event_type", "status", "created_at"
    }
    # Filter auf eine andere Zone liefert den Alarm nicht.
    assert client.get(f"/api/alerts?zone_id={other.id}").json() == []


def test_alerts_filter_by_location_status_and_since(client, db):
    zone = bench_1(db)
    device = new_device(db, zone=zone)
    ingest(db, device.id, 0.10)
    ingest(db, device.id, 0.05)

    by_location = client.get(f"/api/alerts?location_id={zone.location_id}").json()
    assert len(by_location) == 2
    # Neueste zuerst.
    assert by_location[0]["created_at"] >= by_location[1]["created_at"]

    assert client.get(f"/api/alerts?location_id={zone.location_id}&status=resolved").json() == []
    assert len(client.get(f"/api/alerts?location_id={zone.location_id}&status=all").json()) == 2
    assert client.get(f"/api/alerts?location_id={zone.location_id}&since=2999-01-01T00:00:00Z").json() == []


def test_invalid_status_or_limit_is_rejected(client):
    assert client.get("/api/alerts?status=open").status_code == 400
    assert client.get("/api/alerts?limit=0").status_code == 422
    assert client.get("/api/alerts?limit=201").status_code == 422
