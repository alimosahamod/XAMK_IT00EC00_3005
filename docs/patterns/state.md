# State — Actuator lifecycle

## Problem

A pump or a grow light is not just "on" or "off". It can be ready, running, broken or in maintenance, and what you may do depends on where it is now. You cannot start maintenance while the pump is running, and you cannot start a device that is switched off. If this is modelled with booleans like is_running and is_fault plus if checks in the router, the checks get copied, they drift apart, and impossible combinations (running and in maintenance at the same time) become possible.

## Solution

Each lifecycle state is a small object. It knows which commands are possible in it and which state each command leads to. A context holds the current state object and is the only place that changes it. Before every change it asks the current state if the target is allowed.

| Role | In this project |
|------|-----------------|
| State interface | ActuatorState (commands, allowed_commands(), allowed_targets()) |
| Concrete states | OffState, IdleState, RunningState, ErrorState, MaintenanceState |
| Context | ActuatorContext (state, allowed_commands(), transition(target)) |
| Client | ActuatorStateService, called by POST /api/devices/{id}/transition (Phase 10: Command) |

Each concrete state is a dict command → target state. This one dict is the single source of truth. allowed_commands() is its keys, allowed_targets() is its values, so the two can never disagree.

## Legal transitions

| From | Command | To |
|------|---------|----|
| off | power_on | idle |
| idle | start | running |
| idle | start_maintenance | maintenance |
| idle | report_fault | error |
| idle | power_off | off |
| running | stop | idle |
| running | report_fault | error |
| error | reset | idle |
| error | start_maintenance | maintenance |
| maintenance | finish_maintenance | idle |

Every other edge is illegal, for example running → maintenance, running → off, off → running, error → running, maintenance → running and staying in the same state (idle → idle).

Refinement of "* → error": only idle and running can fall into error. An off device does nothing, so it cannot fail while off. A device in maintenance is out of service, and leaves it only through finish_maintenance.

Leaving error always goes through reset (back to idle) or through maintenance. A broken pump can never jump straight back to running.

The command names are generic (start, stop) because the same lifecycle is used for the water pump and the grow light. Phase 10 builds its Command objects on these names.

## Guard

ActuatorContext.transition(target) checks first and changes second:

1. Is target in allowed_targets() of the current state? If not, raise IllegalTransitionError (a ValueError). The state is not changed.
2. Otherwise replace the current state object with the target state object.

An unknown target such as "flying" is simply not an allowed target, so it is rejected in the same way.

## Persistence

| Column | Meaning |
|--------|---------|
| device_id | UUID, primary key and FK to devices, ON DELETE CASCADE |
| state | VARCHAR(32): off, idle, running, error, maintenance (default idle) |
| updated_at | timestamptz, set on insert and on every update |

One row per actuator, so device_id is the primary key. Sensors have no row. Valid names are checked in the domain, not with a CHECK constraint.

Seeding happens in two places. The migration 73521797fd4b_actuator_states runs an INSERT ... SELECT in upgrade() that gives every existing actuator the state idle. New actuators get their idle row in DeviceRepository._to_row, in the same commit as the device itself. INITIAL_STATE = "idle" lives in domain/actuators/state.py.

DeviceRow has a relationship actuator_state with lazy="selectin". The device list loads all states with one extra query instead of one query per device.

## Flow of a transition

ActuatorStateService.transition(device_id, target):

1. Load the device. Missing or not an actuator → DeviceNotFoundError → 404.
2. Load the stored state from actuator_states and build an ActuatorContext.
3. context.transition(target). Illegal → IllegalTransitionError → 409. Nothing is saved.
4. Save the new state and return the device with fresh state and allowed_commands.

The state lives only in the database between requests, never in FastAPI memory, so a restart keeps every state.

## API

| Method | Path | Result |
|--------|------|--------|
| GET | /api/devices | each device has state and allowed_commands (null and [] for sensors) |
| POST | /api/devices/{device_id}/transition | body {"target": "running"}; 200 updated device, 404 missing actuator, 409 illegal transition |

The 409 detail explains the problem, for example "Illegal transition running -> maintenance. Allowed from running: idle, error".

## Frontend

DeviceList shows a state badge on every actuator card: idle slate, running emerald, error red, maintenance amber, off grey outline. The tooltip lists allowed_commands. A small demo control (select a target, Apply) calls the transition endpoint. On success the card is replaced with the returned device, on 409 the backend message is shown under the card. React contains no transition rules. It only shows what the API returns.

## Where to look in code

backend/src/domain/actuators/state.py has the state interface, the five states and get_state.

backend/src/domain/actuators/context.py has ActuatorContext.

backend/src/domain/actuators/errors.py has IllegalTransitionError.

backend/src/application/devices/state_service.py loads, transitions and saves.

backend/src/application/devices/dto.py and mappers.py add state and allowed_commands.

backend/src/infrastructure/persistence/models.py has ActuatorStateRow, actuator_state_repository.py stores it.

backend/src/interfaces/api/devices.py has the transition endpoint.

frontend/src/components/devices/ActuatorStateControl.tsx has the badge and the demo control.

Tests: backend/tests/test_actuator_state.py (all legal and illegal edges, no DB) and backend/tests/test_actuator_state_api.py (Postgres: legal transition updates the row, illegal transition does not, 404 cases).
