# Observer — Domain events and alerts

## Problem

Before Phase 11, nothing happened after a reading, a failed command or a fault. A moisture value below the zone limit was stored and that was it. The obvious fix would be to call an alert writer directly from ReadingService, CommandService and ActuatorStateService. Then every producer would know the alerts table, every new reaction (metrics, a WebSocket in Phase 12) would mean editing all three services again, and one broken listener could make a successful reading fail.

## Intent

Observer defines a one-to-many dependency: when one object reports that something happened, all interested objects are notified, without the reporter knowing who they are. Here the services only say "this happened" by publishing a domain event. Subscribers decide on their own what to do with it.

| Role | In this project |
|------|-----------------|
| Subject | EventBus with subscribe(event_type, handler) and publish(event) (domain/events/bus.py). No unsubscribe. |
| Events | ReadingCreated, ThresholdCrossed, CommandFailed, ActuatorStateChanged, frozen dataclasses (domain/events/events.py) |
| Publishers | ReadingService.take_reading (ingest), CommandService, ActuatorStateService |
| Observers | MoistureThresholdSubscriber, AlertPersistenceSubscriber (application/alerts/subscribers.py) |
| Composition root | build_event_bus / get_event_bus (interfaces/api/event_bus.py): the only place that says who listens to what |

## Event flow

1. Ingest stores a reading. If the device has tracking_enabled, it publishes ReadingCreated with device_id, value, unit, source, recorded_at and the device's location_id and zone_id. With tracking off the reading row is still stored, but no event is published.
2. MoistureThresholdSubscriber.on_reading checks unit == "vwc", a zone_id is set and the value is strictly below zone.moisture_threshold_low. Only then it publishes ThresholdCrossed on the same bus. It writes nothing itself.
3. CommandService publishes CommandFailed when a command ends with status failed (for example "Max run time exceeded" from the Phase 9 decorator), and ActuatorStateChanged when a successful command changed the state.
4. ActuatorStateService publishes ActuatorStateChanged after every saved transition.
5. AlertPersistenceSubscriber is the only code that uses AlertRepository. It inserts one active row per matching event.

| Event | event_type | severity | message |
|-------|------------|----------|---------|
| ThresholdCrossed | threshold.crossed | warning | Moisture below zone low |
| CommandFailed | command.failed | warning | the failure text |
| ActuatorStateChanged, only when state is error | state.changed | critical | Actuator entered error |

location_id and zone_id are copied from the device. For an unassigned device (like the seeded pump) both stay null. Nothing is invented.

## Bus rules

Handlers of one event class run in subscription order. The bus matches the exact event class. If one handler raises, the bus logs it and continues with the next handler. A broken alert writer therefore cannot block other subscribers, and it cannot turn a stored reading into an HTTP error.

The bus is built per request with the request's DB session, so subscribers write in the same session the publisher used. That is also why there is no unsubscribe: the bus lives only for one request.

## Observer vs direct calls

| Services call the alert writer | Services publish events |
|--------------------------------|-------------------------|
| ReadingService, CommandService and ActuatorStateService import AlertRepository | Publishers only import EventBus and the event classes (a test checks this) |
| A new reaction means editing every producer | A new reaction is one new subscriber and one subscribe line |
| One failing reaction breaks the request | The bus isolates a failing handler |
| The threshold rule lives inside the reading service | The threshold rule is its own subscriber |

## API and UI

GET /api/alerts?status=active&location_id=&zone_id=&since=&limit=50 returns alerts newest first. status is active (default), resolved or all; anything else is 400. limit is 1 to 200. The JSON has id, location_id, zone_id, device_id, severity, message, event_type, status and created_at. acknowledged_at is stored but not returned in this phase. There is no ack and no PATCH yet (resolve comes in Phase 13).

The Event feed (#events, frontend/src/components/alerts/EventFeed.tsx) polls this endpoint every 5 seconds, can filter by location id and zone id, shows a severity badge and has an empty state. Because alerts live in the database, they are still there after a page refresh.

## Observer vs Phase 12 WebSocket

Phase 11 uses polling. frontend/src/services/realtime.ts only defines RealtimeEvent and subscribeRealtime, which returns an unsubscribe function and does nothing yet. In Phase 12 a dashboard WebSocket becomes just one more subscriber on this same EventBus (for example for an AlertCreated event after each insert). The socket is a transport, not a second event system, so no pub/sub logic is rebuilt inside socket handlers, and the publishers stay unchanged.

## Tests

backend/tests/test_events.py covers subscription order, a failing handler, tracking on and off, null ids for unassigned devices, the Bench 1 threshold row (0.10 below 0.20, and 0.20 itself not), command.failed on an unassigned pump with "Max run time exceeded", state.changed for target error (and no row for running), the GET filters (zone, location, status, since, limit, 400 for an unknown status) and that the three publishers do not import AlertRepository or AlertRow.
