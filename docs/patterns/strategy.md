# Strategy — Automation per location

## Persistence of the strategy choice

The active strategy is stored in its own table, automation_rules, not as extra columns on locations.

| Column | Meaning |
|--------|---------|
| id | UUID primary key, created by the database |
| location_id | FK to locations, UNIQUE, ON DELETE CASCADE |
| strategy_key | conservative or aggressive |
| parameters | JSONB with optional fine tuning, default {} |
| updated_at | time of the last change |

Why a separate table: automation is its own topic, so LocationRow stays as it was in Phase 4. A location without a rule simply has no row, there are no half-empty columns. Later phases can add more automation data here without touching locations.

The UNIQUE constraint on location_id guarantees at most one active strategy per location. When a location is deleted, its rule is deleted too.

The valid keys are checked in code (get_strategy), not with a CHECK constraint in the database. A third strategy therefore needs no migration.

AutomationRuleRepository.upsert uses INSERT ... ON CONFLICT (location_id) DO UPDATE. This is one atomic statement, so two requests at the same time cannot create a second row or fail on the UNIQUE constraint. updated_at is set explicitly in the upsert, because the ORM onupdate does not run for Core statements.

Code: backend/src/infrastructure/persistence/models.py (AutomationRuleRow), backend/src/infrastructure/persistence/automation_repository.py, migration backend/alembic/versions/1c3a84367de4_automation_rules.py, tests in backend/tests/test_automation_repository.py.
