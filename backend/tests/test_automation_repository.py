from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from infrastructure.db import engine
from infrastructure.persistence.automation_repository import AutomationRuleRepository
from infrastructure.persistence.models import AutomationRuleRow, LocationRow

# Laeuft gegen die echte Postgres-DB, alles in einer aeusseren Transaktion,
# die am Ende zurueckgerollt wird (wie test_readings_api.py).


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


def save_location(db) -> LocationRow:
    location = LocationRow(name="Test location")
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def count_rules(db, location_id) -> int:
    stmt = (
        select(func.count())
        .select_from(AutomationRuleRow)
        .where(AutomationRuleRow.location_id == location_id)
    )
    return db.execute(stmt).scalar_one()


def test_no_rule_returns_none(db):
    location = save_location(db)
    repo = AutomationRuleRepository(db)

    assert repo.get_strategy_key(location.id) is None
    assert repo.get_rule(location.id) is None


def test_upsert_inserts_rule(db):
    location = save_location(db)
    repo = AutomationRuleRepository(db)

    assert repo.upsert(location.id, "conservative") == "conservative"

    assert repo.get_strategy_key(location.id) == "conservative"
    assert repo.get_rule(location.id) == ("conservative", {})
    assert count_rules(db, location.id) == 1


def test_upsert_updates_existing_rule(db):
    location = save_location(db)
    repo = AutomationRuleRepository(db)

    repo.upsert(location.id, "conservative")
    repo.upsert(location.id, "aggressive", {"margin": 0.05})

    assert repo.get_rule(location.id) == ("aggressive", {"margin": 0.05})
    assert count_rules(db, location.id) == 1


def test_rules_are_per_location(db):
    first = save_location(db)
    second = save_location(db)
    repo = AutomationRuleRepository(db)

    repo.upsert(first.id, "conservative")
    repo.upsert(second.id, "aggressive")

    assert repo.get_strategy_key(first.id) == "conservative"
    assert repo.get_strategy_key(second.id) == "aggressive"


def test_second_row_for_same_location_is_rejected(db):
    # Der UNIQUE-Constraint selbst, ohne den Upsert-Weg.
    location = save_location(db)
    AutomationRuleRepository(db).upsert(location.id, "conservative")

    db.add(AutomationRuleRow(location_id=location.id, strategy_key="aggressive"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_upsert_for_unknown_location_fails(db):
    with pytest.raises(IntegrityError):
        AutomationRuleRepository(db).upsert(uuid4(), "conservative")


def test_deleting_location_deletes_rule(db):
    location = save_location(db)
    AutomationRuleRepository(db).upsert(location.id, "conservative")

    db.execute(delete(LocationRow).where(LocationRow.id == location.id))
    db.commit()

    assert count_rules(db, location.id) == 0
