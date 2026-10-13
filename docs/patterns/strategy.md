# Strategy — Automation per location

## Problem

The greenhouse should recommend when to water. There is more than one sensible rule. One rule saves water and waits as long as possible. Another rule waters early to keep the soil wet. If both rules live as if/elif branches in the router or service, every new rule means editing the same method, and the rules cannot be tested on their own.

## Solution

Each rule is its own class behind one interface. The service only asks the selected strategy for a decision and never knows the formula.

| Role | In this project |
|------|-----------------|
| Strategy | AutomationStrategy with decide(context) |
| Concrete strategies | ConservativeMoistureStrategy, AggressiveMoistureStrategy |
| Context object | LocationAutomationContext (location_id, moisture, threshold_low, threshold_high, optional light) |
| Context (user of the strategy) | AutomationService |
| Client | The automation API and the StrategyPanel, which save the key per location |

decide() returns a Recommendation with action (irrigate or wait), reason and an optional score. It only recommends. It never starts a pump. Executing the action is the job of Command in a later phase.

get_strategy(key) picks the strategy from a registry dict. An unknown key raises UnknownStrategyError before decide() runs. The API turns it into 400.

## The two strategies

Both use the band low..high of the zone.

conservative waters only when moisture is below low.

aggressive waters when moisture is below the middle of the band, (low + high) / 2.

Example with the band 0.25–0.45 (middle 0.35):

| Moisture | conservative | aggressive |
|----------|--------------|------------|
| 0.20 | irrigate | irrigate |
| 0.30 | wait | irrigate |
| 0.40 | wait | wait |

So for the same context the two keys give different recommendations between low and the middle.

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

## Flow of evaluate

POST /api/locations/{location_id}/automation/evaluate runs AutomationService.evaluate:

1. Location must exist, otherwise 404.
2. Load the saved strategy_key from automation_rules. No key saved means 409. The request never sends a key.
3. Load low and high of every zone of the location from zones. No zone means 409.
4. Load the newest moisture value from sensor_readings. Only moisture sensors whose devices.location_id is this location count. A sensor without a location is never used. No reading means 409.
5. Build one LocationAutomationContext per zone and call decide().
6. If one zone needs water, its recommendation wins, otherwise the first zone's. The zone name is put in front of the reason.

The strategies only get plain numbers. They never see ORM rows, SQLAlchemy or FastAPI types.

A moisture sensor is linked to a location with PUT /api/locations/{location_id}/sensors/{device_id}. This sets devices.location_id, the column that exists since Phase 4.

## API

| Method | Path | Result |
|--------|------|--------|
| GET | /api/automation/strategies | list of known keys |
| GET | /api/locations/{location_id}/automation | saved key (null if none) |
| PUT | /api/locations/{location_id}/automation | body {"strategy_key": "..."}; 400 unknown key, 404 missing location |
| POST | /api/locations/{location_id}/automation/evaluate | {location_id, strategy_key, action, reason} |
| PUT | /api/locations/{location_id}/sensors/{device_id} | links a moisture sensor, 204 |

## Frontend

StrategyPanel in the #automation card on the dashboard. Enter the location id from the configuration card, choose a key, Save, link a moisture sensor, read the sensor in the sensor list, then Evaluate. The card shows action and reason. After switching the key and pressing Evaluate again, the result changes for the same moisture.

## Where to look in code

backend/src/domain/automation/strategy.py has the interface, both strategies and get_strategy.

backend/src/domain/automation/context.py has LocationAutomationContext and Recommendation.

backend/src/domain/automation/errors.py has the errors.

backend/src/application/automation/service.py builds the context and calls decide().

backend/src/application/automation/dto.py has the DTOs.

backend/src/infrastructure/persistence/automation_repository.py stores the key. LocationRepository.list_zone_thresholds and ReadingRepository.latest_value_for_location load the numbers for the context.

backend/src/interfaces/api/automation.py has the endpoints.

frontend/src/components/automation/StrategyPanel.tsx is the panel.

Tests: backend/tests/test_strategies.py (fake context, both strategies), backend/tests/test_automation_service.py (service with fake repositories), backend/tests/test_automation_api.py (API with seeded zones and readings), backend/tests/test_automation_repository.py.

## Exercise: add a third strategy

Add a strategy that waters only when moisture is far below the band, for example below low − 0.05.

1. Add a class EmergencyOnlyStrategy(AutomationStrategy) with key = "emergency" and its own decide().
2. Add an instance to the registry in strategy.py.
3. Add a test with a fake context.

Nothing else changes: no migration, no change in the service, the router or the frontend. The dropdown loads the keys from GET /api/automation/strategies.
