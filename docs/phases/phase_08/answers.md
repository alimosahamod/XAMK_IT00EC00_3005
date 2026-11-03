# Phase 8 — Answers

## A. Pattern

### 1. Intent of State

The State pattern lets an object change its behaviour when its internal state changes. Each state is its own object, and that object decides what is possible right now. With boolean flags and scattered if guards, every place that changes the actuator has to repeat the same checks. The checks drift apart over time, one place forgets a rule, and the flags can end up in combinations that make no sense, for example running and in maintenance at the same time.

### 2. Participants and transitions

The context is ActuatorContext. It holds the current state object and is the only place that may change it. The state interface is ActuatorState, which offers allowed_commands() and allowed_targets(). The concrete states are OffState, IdleState, RunningState, ErrorState and MaintenanceState. Each one has a small dict that maps a command to the next state. The client is ActuatorStateService, which is called by the transition endpoint today and by Command in Phase 10.

A transition works like this. The service loads the stored state and builds the context. It calls transition(target). The context asks the current state object whether the target is allowed. If yes, the context swaps in the new state object and the service saves it. If no, the context raises IllegalTransitionError and nothing changes. The guards live inside the state objects, because each state lists its own legal moves, and the context enforces them in one single method.

### 3. Purpose of allowed_commands

allowed_commands answers the question "what can I do now?" for the current state. For an idle pump it returns start, start_maintenance, report_fault and power_off. For a running pump it returns only stop and report_fault. If the UI only got the raw string "running", it would have to know the rules itself and copy them into React. That copy can go wrong or get out of date when the backend rules change. When the backend sends the list, the rules exist in one place only, and the UI simply shows what it gets.

## B. This phase of the application

### 4. Implemented states and legal transitions

I implemented all five states: off, idle, running, error and maintenance. From off, power_on moves to idle. From idle, start moves to running, start_maintenance moves to maintenance, report_fault moves to error and power_off moves to off. From running, stop moves back to idle and report_fault moves to error. From error, reset moves to idle and start_maintenance moves to maintenance. From maintenance, finish_maintenance moves back to idle.

So only idle and running can fall into error, because an off device does nothing and a device in maintenance is out of service. To leave error you must reset or go to maintenance. A broken pump can never jump straight back to running. Everything else is illegal, for example running to maintenance or off to running.

### 5. Why the state is stored in actuator_states

The backend process can restart at any time, for example after a code change, a crash or a new deployment. If the state only lived in memory, every pump would look idle again after a restart, even if it was broken or in maintenance. That would be dangerous, because a broken pump could be started again. Several backend workers would also each have their own copy. After a restart, every actuator must still have exactly the state it had before. I tested this by moving a grow light to running, restarting uvicorn, and seeing that it was still running with the same allowed_commands.

### 6. Illegal transitions

An illegal transition must not reach the database, because the stored state is the truth that the whole system trusts. If an illegal value was saved, the next request would start from an impossible state, and the device and the database would no longer match. In ActuatorStateService the context checks first and raises the error, so the save line is never reached. The test test_illegal_transition_does_not_update_row checks this against real Postgres.

I return 409 Conflict. The request body is well formed, so it is not really a bad request (400). It only fails because it conflicts with the current state of the resource. The same request would work from another state. The rule belongs in the domain and not in React, because the frontend is not the only client. Scalar, scripts, tests and later Phase 10 Command all call the API, and a check in React could simply be skipped by any of them.

### 7. How the dashboard uses state and allowed_commands

Every actuator card in the Devices section shows a coloured badge for its state: slate for idle, emerald for running, red for error, amber for maintenance and a grey outline for off. When you hover over the badge, a tooltip lists the allowed_commands. A small demo control lets you choose a target state and press Apply. On success the card shows the new state at once. On a 409 the card shows the backend message, for example "Illegal transition running -> maintenance. Allowed from running: idle, error". React never decides what is legal.

This prepares Phase 10 Command. The command names like start and stop already exist in the state objects, and Command can check allowed_commands before it executes. The UI can then show real buttons only for the commands in the list.

## C. Compare, contrast, and scenarios

### 8. State versus Strategy

Both patterns have a context that delegates to an object, but the reason is different. In Strategy, the client or the user picks the object from outside, and it stays until someone picks another one. It is a selectable policy. In State, the object is replaced as a result of the object's own transitions. It is a lifecycle, and the state objects decide which next states are possible.

In Phase 6 a user picks the conservative or aggressive strategy for a location. Both are always valid choices, and neither one knows about the other. In Phase 8 an actuator moves from idle to running to error and back to idle. Not every move is possible, and the current state decides which moves are legal.

### 9. State versus a pile of booleans

With three booleans like is_running, is_fault and is_maintenance there are eight combinations, but only a few of them are real situations. Nothing stops code from setting is_running and is_maintenance to true at the same time, especially when different parts of the code change different flags. Every reader then has to guess what that combination means.

With explicit states the actuator is always in exactly one state, stored in one column. Impossible combinations cannot even be written down. Because every change goes through transition() and the commands dict of the current state, an edge that is not listed simply does not exist.

### 10. Two traps

If a concrete state maps HTTP status codes or commits with SQLAlchemy, the domain depends on FastAPI and the database. The state can then no longer be tested without a web server or a DB, and it cannot be reused by Phase 10 Command or a background job. It also makes the order of things unclear. The rule is checked, saved, and turned into an HTTP answer all in one place, and nobody can check the rule first and save only afterwards. In my code the state only knows its commands, the service saves, and the router maps errors to 404 or 409.

If a state changes a flag directly and skips transition(), the guard is bypassed. The change is not checked, the error is never raised, and the illegal state can be saved. The state machine then lies, because the commands dict says one thing and the stored data says another. All changes must go through the one guarded method, otherwise the pattern gives no protection.

AI assistants (Google Gemini and Claude) were used to formulate answers, assist with the code, and provide troubleshooting advice during development.
