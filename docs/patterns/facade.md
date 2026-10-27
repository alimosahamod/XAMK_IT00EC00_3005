# Facade — Location overview

## Problem

The dashboard wants one snapshot of a location: its name, how many sensors and actuators it has, the newest readings, the saved strategy and the current recommendation. This data already exists from Phases 2–6, but it is spread over several tables, repositories and the AutomationService.

Without a facade, the router (or React) would have to know all of these parts, call them in the right order and handle their errors. Every new screen would copy the same steps, and a change in one step would break all copies.

## Solution

LocationOverviewFacade offers one method, get_overview(location_id), that returns one LocationOverviewDto. The facade only orchestrates. It calls the existing collaborators and puts their results together:

LocationRepository.get_name() gives the name, or the facade raises LocationNotFoundError.

DeviceRepository.count_by_role() gives the sensor and actuator counts.

ReadingRepository.latest_per_device_for_location() gives the newest reading of every device at the location.

AutomationService.get_rule() gives the strategy_key.

AutomationService.evaluate() gives the recommendation.

## What it hides

The client does not know which repositories exist, in which order they are called, or how the recommendation is made. It also does not know that "not ready" (no strategy, zone or moisture reading) is turned into last_recommendation = null. Other errors are not hidden: a missing location becomes a 404, and unexpected errors still reach the client as errors.

The facade does not re-implement any logic. Thresholds and conservative/aggressive stay in the Strategy classes, unit translation stays in the Adapters, and SQL stays in the repositories.

## Last recommendation

The recommendation is computed on every request by calling AutomationService.evaluate(). It is not stored. So it always matches the current DB state and no new table is needed.

## Database

No new table and no migration. The existing tables (locations, zones, devices, sensor_readings, automation_rules) are enough. The optional view was skipped.

## N+1 note

An N+1 problem would be: load all devices (1 query), then load the newest reading for each device in a loop (N queries). With 50 sensors that is 51 queries.

Instead, latest_per_device_for_location() uses one query with DISTINCT ON (device_id) ordered by recorded_at DESC. It fits the index on (device_id, recorded_at DESC). Device counts are one GROUP BY role query. So get_overview() runs a small, fixed number of queries, no matter how many devices a location has.

## Flow

GET /api/locations/{location_id}/overview calls only the facade. The router gets the facade through LocationOverviewFacade.from_session(db) and does not import any repository. LocationNotFoundError becomes 404. The response schema is shown in Scalar.

The Overview card on the dashboard makes one fetchOverview(locationId) call and renders cards from the DTO. A refresh button calls the same endpoint again. Because nothing is cached, a new reading or a changed strategy shows up on the next request without extra frontend code.

## Where to look in code

backend/src/application/overview/dto.py has LocationOverviewDto and its parts.

backend/src/application/overview/facade.py has LocationOverviewFacade.

backend/src/interfaces/api/overview.py has the overview route.

backend/tests/test_overview_api.py has the integration tests.

frontend/src/components/overview/OverviewPanel.tsx has the Overview card.
