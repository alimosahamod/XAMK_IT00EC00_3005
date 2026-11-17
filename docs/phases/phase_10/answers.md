# Phase 10 — Answers

## 1. Intent of Command

Command turns a request into an object. Instead of calling actuator.start() and forgetting about it, the application creates a StartPumpCommand that knows which device it is for, what payload it carries and which receivers it talks to. Objectifying a request means that the request itself becomes data that can be passed around and kept. With a bare call there is nothing left once it returns. With an object we can write it into an audit log, show it in a history table, put it in a queue for later, retry it, or remember enough about it to undo it. In our greenhouse the most important gain is the audit trail in command_log, where every attempt is stored with its outcome.

## 2. Participants

The command is the object with execute(), here StartPumpCommand, StopPumpCommand, SetLightLevelCommand and SwitchOffLightCommand, which all share the flow in ActuatorCommand. The receivers are the objects that really change something: the decorated ActuatorPort from Phase 9, which drives the (simulated) hardware, and the actuator state through ActuatorContext and ActuatorStateRepository from Phase 8. The invoker is CommandInvoker, which triggers execute() and records the result. The client is CommandService, called by the POST /api/commands handler. It creates the command through the registry and hands it to the invoker. So the client creates the command, the invoker triggers execute(), and only the receivers change hardware or actuator state.

## 3. Capturing undo data

A command that supports undo must capture the data it needs for the reversal inside execute(), before it changes anything. For SetLightLevelCommand that would be the previous level and the previous state of the light. Capturing before mutating is critical because after the mutation the old value is gone. If the command read the level afterwards, it would only see the new value and undo would restore the wrong thing. We did not implement undo, because some actions like pumped water cannot really be reversed, but if we add it, this rule applies.

## 4. Implemented commands and why the router uses the invoker

I implemented start_pump, stop_pump, set_light_level (payload with a level from 0 to 100) and switch_off_light. The HTTP handler only passes command_type, device_id and payload to CommandService, which builds the command and gives it to the invoker. The router never calls the actuator adapter itself. If it did, every endpoint would have to repeat the state check, the mapping from a command name to a port command and target state, and the logging. One forgotten check would let an illegal action through. With the invoker, all commands go through the same path, every attempt is logged, and a new command needs only a new class and a registry entry, not a new branch in the router.

## 5. Execute path

First the command loads the current state into an ActuatorContext and checks whether its state command, for example start, is in allowed_commands. If it is not, it raises CommandRejectedError and the invoker writes a rejected row. If it is allowed, the command calls apply on the decorated port, so logging and maxRunTime run as in Phase 9. Only if apply succeeds is the state transition done and saved to actuator_states. Finally the invoker writes success, or failed if apply raised an error. A rejected command must not change the state because the state machine has just said the action is illegal. Changing it anyway would make actuator_states lie about the real device. It must not reach apply either, because then the hardware would act, for example a pump in maintenance would start running while a technician works on it.

## 6. Rejected, failed and success

Rejected means the command was not allowed in the current state and nothing was done. An example is start_pump while the pump is in maintenance. Failed means the command was allowed, but the decorator stack or the adapter stopped it. An example is stop_pump on a pump that has been running longer than the max run time, so the maxRunTime decorator blocks it. Success means the command passed the guard, apply worked and the state was updated, for example start_pump on an idle pump, which is now running. Illegal in this state is a decision of the lifecycle rules that is made before anything happens. A policy or adapter error happens after the command was accepted, while trying to carry it out. The first points to a wrong request from the operator, the second to a problem in execution, so they need different follow-up.

## 7. Why command_log is separate from actuator_execution_log

command_log records operator intent: which command someone asked for, for which device, with which payload, and how it ended. actuator_execution_log from Phase 9 records what happened inside the decorator stack: which policies were applied and whether the adapter call succeeded. A rejected command appears only in command_log, because it never reached the port. A failed command appears in both, once as the failed intent and once as the blocked execution. Keeping them apart means each table answers one question: what the operator wanted, and what the actuator layer actually did with it.

## 8. Command vs Strategy

Strategy is an interchangeable algorithm that decides something. In Phase 6 the conservative or aggressive strategy only looks at moisture values and recommends irrigate or wait, without any side effect. Command is a request that changes something in the world and leaves a history. They work together in a clear order: the strategy recommends irrigate, and an operator or later an automation turns that recommendation into a start_pump command that is checked against the state, executed through the port and logged. Strategy answers what should be done, Command does it and remembers that it did.

## 9. Command vs State

The command triggers the action, it is the request "start this pump". The state object decides whether this request is legal right now, by offering or not offering start in allowed_commands. The command asks the ActuatorContext before it touches the port and uses transition() to change the state, so the lifecycle rules stay in one place. Commands must not bypass these guards. Otherwise the state machine from Phase 8 would only be decoration, and a command could move a device into a combination that the rules forbid, for example running while in maintenance.

## 10. Why the backend still rejects

The UI disables buttons that are not in allowed_commands, but this only helps the user. The UI can be out of date, for example when a second tab or the automation changed the state a moment ago. Also anyone can send a request directly to POST /api/commands with curl or a script and skip the UI entirely. So the only check that is guaranteed to run is the guard in the backend command. If a classmate's command called the raw adapter instead of the decorated port and skipped the state guard, a pump in maintenance could start, actuator_states would no longer match the device, the maxRunTime policy would not protect the pump, and the execution log would not show the attempt. The safety rules of Phases 8 and 9 would simply not exist for that command.

AI assistants (Google Gemini and Claude) were used to formulate answers, assist with the code, and provide troubleshooting advice during development.
