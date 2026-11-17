# Command — Actuator actions as auditable objects

## Problem

Until Phase 9 an actuator action was a plain method call, port.apply(device_id, "on", payload). Once the call returned, nothing remained: no record of who wanted what, no way to see rejected attempts, and nothing to queue or replay. If the router called the port itself, every endpoint would also have to repeat the state check from Phase 8, and one forgotten check would let a pump start while it is in maintenance.

## Intent

Command turns a request into an object. The object carries everything needed to run it (command type, device, payload, and the receivers it talks to) and offers one method, execute(). Because the request is now a thing and not just a call, it can be logged, listed, queued or retried, and the code that triggers it does not need to know what it does.

| Role | In this project |
|------|-----------------|
| Command | Command (execute()) and ActuatorCommand with the shared guard → port → state flow (domain/commands/base.py) |
| Concrete commands | StartPumpCommand, StopPumpCommand (pump.py), SetLightLevelCommand, SwitchOffLightCommand (light.py) |
| Receivers | the decorated ActuatorPort from build_actuator (Phase 9) and the actuator state via ActuatorContext / ActuatorStateRepository (Phase 8) |
| Invoker | CommandInvoker.submit(command) (domain/commands/invoker.py) |
| Client | CommandService (application/commands/service.py), called by POST /api/commands |
| Factory | registry COMMANDS: command_type → class, create_command(...) (domain/commands/registry.py) |

A concrete command only sets four class attributes: command_type ("start_pump"), port_command ("on"), state_command (the name in allowed_commands, "start") and target_state ("running"). The flow itself lives once in ActuatorCommand.execute().

## Execute path

1. Guard. Load the state from actuator_states into an ActuatorContext. If state_command is not in allowed_commands(), raise CommandRejectedError. The port is not called and the state is not touched.
2. Port. Call apply() on the decorated ActuatorPort (logging → maxRunTime → simulation). If a decorator blocks, the exception ends execute() here, so the state stays as it was. The logging decorator has already written a failed row to actuator_execution_log.
3. State. Only after a successful apply: ActuatorContext.transition(target_state) and save it.
4. Audit. The invoker turns the outcome into a status and writes one row to command_log: success (no exception), rejected (CommandRejectedError) or failed (any other exception, with its message).

SetLightLevelCommand overrides is_allowed(): it may switch the light on from idle and may also change the level of a light that is already running (then the state stays running).

## Invoker

CommandInvoker knows nothing about pumps or lights. It calls command.execute() and logs the result. Choosing the class for a command_type happens in a dictionary, not in an if/elif chain. Adding a command means one new class and one registry entry; the invoker, the service and the router stay unchanged. SwitchOffLightCommand was added this way.

## Command vs calling the port in the router

| Port called from the router | Command + invoker |
|-----------------------------|-------------------|
| The router must remember the state check, and each new endpoint can forget it | The guard is part of every command's execute(), so no caller can skip it |
| Only successful hardware calls leave a trace (in the execution log) | Every attempt, including rejected ones, is a row in command_log |
| Mapping "start" to "on" and to the next state is spread over HTTP code | Each command object knows its port command and target state |
| The router grows an if/elif per device action | The router only passes command_type, device_id and payload on |

The Phase 9 demo route POST /api/actuators/{id}/apply did exactly the left column, so it was removed. The only way to the actuator port is now through a command.

## Persistence

| Column | Meaning |
|--------|---------|
| id | UUID primary key |
| command_type | VARCHAR, e.g. start_pump |
| device_id | UUID, FK to devices, ON DELETE CASCADE |
| payload | JSONB, e.g. {"level": 70} |
| status | success, failed or rejected |
| error_message | text, nullable |
| created_at | timestamptz, indexed, newest first in the API |

command_log stores operator intent and its outcome. actuator_execution_log (Phase 9) stores what happened inside the decorator stack. A rejected command appears only in command_log, because it never reached the port.

## API

POST /api/commands with body `{ command_type, device_id, payload? }` returns `{ command_type, device_id, payload, status, error_message }`.

Status codes: 200 for every processed command, including rejected and failed. The outcome is in status, and the row is in command_log in all three cases. This is a deliberate choice: the request was valid and was recorded; whether the actuator moved is part of the result. 400 means unknown command_type or invalid payload, 404 means the device does not exist or is not an actuator. In both error cases no command object is built and nothing is logged.

GET /api/commands?limit=50 returns command_log rows, newest first. Both routes are documented in Scalar under "commands".

## UI

The "Controls" card (#controls, frontend/src/components/commands/ActuatorControls.tsx) shows each actuator with its state badge. Pumps get Start and Stop, grow lights get a level slider with "Set level" and "Switch off". A button is disabled when allowed_commands does not contain the state command it needs. This is only convenience; the backend guard is the real check. After each command the dashboard reloads the actuators, the "Command history" table (CommandHistory.tsx) and the execution log.

## Undo

Undo is optional in the lab and not implemented. A real undo would have to capture the previous state and light level before execute() changes them. Some actions cannot be undone safely (water already pumped), so the audit trail is the main benefit here.
