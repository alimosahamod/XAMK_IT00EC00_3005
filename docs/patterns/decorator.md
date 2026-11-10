# Decorator — Policies around the actuator port

## Problem

Every actuator command should get extra rules around it: write each attempt into a log, and block the command if the actuator has been running for too long. More rules will follow (retry, permissions, rate limits). Putting these rules as if checks into the router mixes HTTP and policy code, and every new rule touches old code. Building them with inheritance (LoggingActuator, MaxRunTimeActuator, LoggingMaxRunTimeActuator, …) needs one subclass per combination, which grows exponentially.

## Solution

Each rule is its own small class that implements the same ActuatorPort as the real adapter and holds an inner ActuatorPort. In apply() it does its own work before or after the call and then delegates to the inner object. Because every layer has the same interface, layers can be stacked like onion skins, and the caller cannot tell how many there are.

| Role | In this project |
|------|-----------------|
| Component | ActuatorPort.apply(device_id, command, payload) (domain/actuators/ports.py) |
| Concrete component | SimulationActuatorAdapter (infrastructure/adapters/actuators/simulation.py) |
| Decorator base | ActuatorDecorator: implements ActuatorPort, holds `_inner`, collects policy names |
| Concrete decorators | LoggingActuatorDecorator ("logging"), MaxRunTimeActuatorDecorator ("maxRunTime") |
| Composition root | build_actuator(db) in application/actuators/actuator_chain.py |
| Client | ActuatorExecutionService, called by POST /api/actuators/{id}/apply (Phase 10: Command) |

## Wrapping and order

```text
LoggingActuatorDecorator  ->  MaxRunTimeActuatorDecorator  ->  SimulationActuatorAdapter
       (outer)                        (middle)                         (inner)
```

The order is defined in exactly one place, build_actuator(db). It reads from the inside out: first the simulation adapter, then the max-run-time policy around it, then logging around everything.

Logging is outermost on purpose. It sees every logical call, including the ones that maxRunTime blocks. If logging were inside maxRunTime, a blocked call would never reach it, so blocked attempts would silently disappear from the log.

## Max run time

MaxRunTimeActuatorDecorator asks ActuatorStateRepository.get_running_since(device_id). That returns actuator_states.updated_at when the state is running (Phase 8), otherwise None. If now minus that time is larger than the limit (setting actuator_max_run_time_s, default 1800 s), it raises PolicyViolationError("maxRunTime", "Max run time exceeded") and does not call the inner adapter. The clock is injectable, so tests can fix the time.

The decorator does not keep its own "running since" timer. The lifecycle belongs to State (Phase 8); the decorator only reads it.

## Execution log

LoggingActuatorDecorator calls the inner layer inside try/except. On success it writes a row with success=true; on any exception it writes success=false with the error message and re-raises, so the caller still sees the failure. policy_applied is the list of policy names of the whole stack, inner to outer, for example ["maxRunTime", "logging"].

| Column | Meaning |
|--------|---------|
| id | UUID primary key |
| device_id | UUID, FK to devices, ON DELETE CASCADE |
| success | boolean |
| policy_applied | JSONB list of policy names |
| message | text, nullable (e.g. "Max run time exceeded") |
| created_at | timestamptz, indexed, newest first in the API |

## API and UI

GET /api/actuators/executions?limit=20 returns the newest rows as `{ id, device_id, success, policy_applied, message, created_at }`. POST /api/actuators/{device_id}/apply is a demo route until Phase 10. It returns 204 on success, 409 when a policy blocks (the row is already written), and 404 for unknown devices. The router contains no policy checks; it only translates errors to HTTP.

The dashboard panel "Execution log" (frontend/src/components/actuators/ExecutionLog.tsx) lists time, device, a success/failed badge, policies and message, with an empty state.

Demo: set an actuator to running, let it run longer than the limit (or set ACTUATOR_MAX_RUN_TIME_S=10 in .env and wait 10 seconds), click Send "on" and the table shows a failed row with maxRunTime, logging.

## Decorator vs inheritance

With inheritance, behaviour is fixed at class-definition time and every combination is a new class. With decorators, behaviour is composed at runtime: adding a policy means one new class plus one line in build_actuator; removing it means deleting that line. Each policy is tested on its own with fakes (tests/test_actuator_decorators.py), and the real stack is tested against Postgres (tests/test_actuator_executions_api.py).

## Decorator vs Adapter

The Phase 5 adapters change an interface: VendorStubSensorAdapter translates the vendor's raw dict (sensorRef, val, uom, epoch ms) into SensorPort's Reading, and SimulationActuatorAdapter puts the simulation behind ActuatorPort. A decorator keeps ActuatorPort exactly as it is and only adds behaviour around it.
