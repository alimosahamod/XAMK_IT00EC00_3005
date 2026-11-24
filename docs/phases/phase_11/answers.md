# Phase 11 — Answers

## A. Pattern

### 1. Intent of Observer

Observer means: when something happens in one object, many other objects are told about it automatically, and each of them reacts in its own way. The one-to-many dependency in our greenhouse is one event, for example a stored moisture reading, and several possible listeners that care about it. Today these are the threshold check and the alert writer. In Phase 12 a WebSocket will join them. The subject must notify the listeners without knowing their concrete classes, because otherwise ReadingService would have to import and call every listener by name. Then each new listener would mean a change in the producer, the producer would be hard to test, and an error in one listener could break the reading itself.

### 2. Participants

The subject is our EventBus. It keeps a list of handlers for each event class. The observers or subscribers are MoistureThresholdSubscriber and AlertPersistenceSubscriber. These two are also the concrete observers, because they are the real classes with real reactions. The events are small frozen dataclasses: ReadingCreated, ThresholdCrossed, CommandFailed and ActuatorStateChanged. The publishers are the application services that do the real work and then report it: ReadingService for ingest, CommandService and ActuatorStateService. The method subscribe registers a handler for one event class. The method publish delivers an event to all handlers of its class, in the order they subscribed. An unsubscribe method would remove a handler again. Our EventBus does not have it, because the bus is built fresh for each request and never needs to remove anyone.

### 3. When to use it and when to skip it

Use Observer when one action must cause several independent reactions, when new reactions will be added later, or when you want one central place where a later real-time channel can plug in. That is exactly our case: alerts now, metrics maybe, and a WebSocket in Phase 12. Skip it when there will only ever be one listener, because a direct method call is simpler and easier to follow. Also skip it when you need a strict workflow with many steps and a guaranteed order, where each step depends on the result of the step before. Then an explicit service that calls the steps one after another, or a real message queue with clear contracts, is the better tool.

## B. This phase of the application

### 4. Domain events and who publishes them

We publish four domain events. ReadingCreated (reading.created) is published after a reading is stored, but only when the device has tracking_enabled set to true. ThresholdCrossed (threshold.crossed) is published by MoistureThresholdSubscriber when a vwc reading in a zone is strictly below the zone's moisture_threshold_low. CommandFailed (command.failed) is published by CommandService when a command ends with status failed. ActuatorStateChanged (state.changed) is published after every saved state change, both by ActuatorStateService and by CommandService. The persistence subscriber only stores it as an alert when the new state is error.

ReadingService.take_reading publishes reading.created. It is the one ingest path. In our project the manual read uses it, and a simulation sampler or an MQTT translation must call the same method. If each source had its own publish code, the rules could drift apart, for example one source could forget the tracking check or forget to copy zone_id. With one path the rule exists once. A publisher must not import the alerts repository or the UI, because then it would be coupled to one specific reaction again. The whole point is that the reading service only says "a reading was stored" and does not know what happens next. A test checks that the three publishers do not contain AlertRepository or AlertRow.

### 5. What AlertPersistenceSubscriber does

When AlertPersistenceSubscriber gets an event, it turns it into exactly one active row in the alerts table, with the location_id, zone_id and device_id from the event. For ThresholdCrossed it stores event type threshold.crossed, severity warning and message "Moisture below zone low". For CommandFailed it stores command.failed, severity warning and the failure text, for example "Max run time exceeded". For ActuatorStateChanged it stores state.changed, severity critical and "Actuator entered error", but only if the state is error. Other states are ignored. Alerts live in the database and not only in React state, because React state disappears when the page reloads. The event feed reads the alerts from GET /api/alerts, so after a refresh it simply loads the same rows again.

### 6. Why polling is enough in this phase

In this phase the goal is to learn the event bus and to make the alerts permanent. Polling GET /api/alerts every 5 seconds is enough to show that an alert appears after a low reading. A WebSocket would add connection handling, reconnects and server push, which is a separate topic for Phase 12. That is why services/realtime.ts is only a stub with RealtimeEvent and a subscribeRealtime function that returns an empty unsubscribe function. In Phase 12 the dashboard socket should become one more subscriber on this same EventBus. After each alert insert an AlertCreated event can be published, and the socket subscriber sends it to the browser. The socket is only a new transport. It must not contain its own list of listeners or its own publish logic.

### 7. The must-demo path

A sensor on Bench 1 has tracking_enabled true and the zone's low threshold is 0.20. A reading of 0.10 comes in through POST /api/sensors/{id}/read. ReadingService stores the reading and publishes ReadingCreated with the device's location_id and zone_id. The EventBus calls MoistureThresholdSubscriber, which sees that 0.10 is below 0.20 and publishes ThresholdCrossed. The bus then calls AlertPersistenceSubscriber, which inserts the threshold.crossed row through AlertRepository. The alerts router reads that row, and the EventFeed shows it at the next poll, also when it is filtered to Bench 1. The reading service and the sensor router must not write the alert directly. Only the persistence subscriber does that. When tracking_enabled is false, the reading row is still stored in sensor_readings, but ReadingCreated is not published, so there is no threshold check and no alert.

## C. Compare, contrast, and scenarios

### 8. Observer vs Facade

Facade makes it easy to call into a subsystem. The caller asks one object, and that object talks to many parts behind it. Observer goes the other way. One object reports that something happened, and many listeners react after it. In our greenhouse the Phase 7 overview is a Facade: one request to the overview returns devices, latest readings, strategy and recommendation, and the facade collects all of that. In this phase the EventBus is the Observer: ReadingService publishes one event and does not know that a threshold check and an alert writer react to it. The Facade pulls information together on request, and the Observer pushes news out after a change.

### 9. Observer vs Command

Command captures an intent to act, for example "stop this pump". Observer spreads the outcome, for example "stopping this pump failed". In our code the command object runs execute() inside the CommandInvoker, and the invoker records the result as success, failed or rejected. After that, CommandService looks at the result and publishes CommandFailed or ActuatorStateChanged on the bus. The command class itself never knows who stores alerts. It only does its job, the service reports the outcome as an event, and AlertPersistenceSubscriber, which was subscribed in the composition root, decides to write the row. So we could add a new reaction to failed commands without touching any command class.

### 10. A failing subscriber

If one subscriber throws an exception and the bus does not catch it, the loop stops and the later subscribers never run. That is a trap, because the subscribers are supposed to be independent. A database problem in the alert writer would then also stop metrics or, in Phase 12, the WebSocket push, and the error could even travel back to the publisher and turn a stored reading into a failed HTTP request. Our EventBus avoids this. It calls each handler inside its own try and except, logs the error with the handler name and the event type, and then goes on with the next handler. A test checks that a broken handler does not stop a later one. The alert repository also does a rollback after a failed commit, so the database session stays usable for the next subscriber.
