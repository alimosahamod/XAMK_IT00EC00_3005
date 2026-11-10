# Phase 9 — Answers

## A. Pattern

### 1. Intent of Decorator

Decorator adds extra behaviour to an object by wrapping it in another object that has the same interface. The wrapper does its own work before or after the call and then passes the call on to the object inside. Because every wrapper looks like the original, wrappers can be stacked in any number and any order. With subclasses, every combination of behaviours needs its own class, so logging, retry and max run time would already lead to classes like LoggingRetryMaxRuntimeActuator and many more. With wrappers, each behaviour is written once as one small class, and combinations are built by stacking them at runtime instead of writing a new class.

### 2. Participants

The component is the shared interface, here ActuatorPort with its method apply(device_id, command, payload). The concrete component is the real object that does the core work, here SimulationActuatorAdapter. The decorator is a class that implements the component and holds a reference to an inner component, here the base class ActuatorDecorator. The concrete decorators add one specific behaviour each, here LoggingActuatorDecorator and MaxRunTimeActuatorDecorator.

Every decorator presents exactly the same apply method to the caller. This must match the wrapped component, because the caller and every outer decorator only know ActuatorPort. If one layer had a different method or signature, it could not be placed inside another layer, and the caller would have to know which concrete wrapper it is talking to. Then the stack would no longer be freely composable.

### 3. Order matters

Take logging and max run time. In our stack, logging is outside and max run time is inside. When max run time blocks a command, the exception travels out through the logging layer, so logging still writes a row with success=false. If we turned it around and put max run time outside, a blocked command would stop before it ever reached logging. The attempt would vanish without any row in the log.

The same is true for logging and retry. If logging wraps retry, you see one log entry per logical call, no matter how many retries happened inside. If retry wraps logging, every single attempt is logged, so one call with two failures produces three entries. Both can be useful, but they show different things, so the order must be chosen on purpose.

## B. This phase of the application

### 4. ActuatorPort, decorators and wiring

ActuatorPort is the domain interface for every actuator. It has one method, apply(device_id, command, payload), and nothing above it needs to know whether a simulation or real hardware is behind it. Around the SimulationActuatorAdapter I stacked two decorators. MaxRunTimeActuatorDecorator blocks a command when the actuator has been running longer than the configured limit. LoggingActuatorDecorator writes every attempt into actuator_execution_log.

The chain is wired in build_actuator(db) in application/actuators/actuator_chain.py, which is our composition root. ActuatorExecutionService gets the finished port from there. It is not built in the HTTP router because the router should only translate HTTP into calls and errors into status codes. If the router built the chain or contained policy checks, the rules would be tied to one endpoint, and Phase 10 Command or any other caller would have to copy them. With one composition root, every caller gets the same stack in the same order.

### 5. Why a blocked attempt still needs a row

A blocked attempt is often the most important event to see. It means someone or something tried to keep a pump or light running for too long, which could flood a bed or waste energy. If only successful calls were logged, the log would hide exactly the cases where the safety rule protected the greenhouse. Writing success=false together with the policy names in policy_applied makes it clear what happened and which rule stopped it. This works because logging is outermost: the inner adapter is never called, but the exception still passes through the logging layer, which records it and then re-raises it.

### 6. How max run time knows the duration

The decorator calls ActuatorStateRepository.get_running_since(device_id). If the stored state in actuator_states is running, this returns updated_at, which is the moment of the last transition into running from Phase 8. The decorator then compares now minus that time with the limit from the setting actuator_max_run_time_s. The clock is passed in as a function, so tests can fix the time.

This data must come from State because State already owns the lifecycle of the actuator and saves it in the database. If the decorator kept its own timer, there would be two sources of truth that could disagree, for example after a restart or when the state is changed through another route. The decorator should only apply a policy on top of the existing lifecycle, not invent a second one.

### 7. Why persist the log

Output on stdout is lost when the process restarts, is spread across different containers, and cannot be queried by the dashboard. A database table survives restarts, can be filtered and sorted, and can be served through an API. That is why GET /api/actuators/executions reads directly from actuator_execution_log, newest first.

After a blocked attempt and a refresh, the Execution log panel shows a new row at the top with the device name, a red failed badge, the policies maxRunTime and logging, and the message Max run time exceeded.

## C. Compare, contrast, and scenarios

### 8. Decorator vs Adapter

Decorator keeps the interface and adds behaviour. Adapter changes the interface and translates. In this greenhouse, Phase 9 is the Decorator: LoggingActuatorDecorator and MaxRunTimeActuatorDecorator both take an ActuatorPort and are an ActuatorPort, and only add logging and a safety check. Phase 5 is the Adapter: for example VendorStubSensorAdapter takes the vendor's raw format with fields like sensorRef, val and uom and translates it into the Reading that SensorPort expects. The simulation actuator adapter from Phase 5 is the innermost object that the decorators now wrap.

### 9. Decorator vs inheritance

With inheritance, the combination of policies is fixed when the class is written. Logging plus max run time is one class, max run time alone is another, and adding retry doubles the number of classes again. Removing one policy from a combined subclass means writing yet another class. With composition, each policy is one class, and build_actuator decides which ones to use. Adding a policy means writing one new decorator and adding one line to the composition root. Removing it means deleting that line. No other class has to change, and each policy can be tested on its own.

### 10. The two traps

If a decorator changes the method signature, for example by requiring an extra argument or returning something different, it no longer implements the same interface. It cannot be placed inside or around other decorators anymore, and the caller suddenly has to know which concrete wrapper it holds. That destroys the main benefit of the pattern, which is that callers only see one port and the stack can be rearranged freely. In that case it is really an adapter, not a decorator.

Ignoring wrap order is a trap because order changes what the system does. If logging sits inside a policy, blocked attempts are never logged. If logging sits inside retry, one logical call creates several rows. A developer who cannot say whether logging runs once per logical call or once per inner attempt cannot explain what the log means, and cannot trust the numbers on the dashboard. The order should be written in one place and documented. In this project it is written in build_actuator and documented in docs/patterns/decorator.md.

AI assistants (Google Gemini and Claude) were used to formulate answers, assist with the code, and provide troubleshooting advice during development.
