# Phase 2 — Answers

## A. Pattern

1. Intent of Factory Method
Factory Method lets a caller ask for an object without knowing the exact class. The problem with scattered new/constructors is that adding a new type means editing many places. That is easy to forget and easy to break.

2. Main participants
- Product: the common type the client uses.
- Concrete product: a real variant.
- Creator: the interface with the factory method.
- Concrete creator: builds one product variant.
- Client: uses the creator, not the concrete classes.

3. Adding a new variant
With polymorphic creators you add one new class and one registry entry, and you touch nothing else. With one shared if/elif you must open and edit that function every time. The first way is safer for extension because old code stays untouched.

## B. This phase of the application

4. Product and concrete creators
The product is Sensor. The concrete creators are MoistureSensorCreator and LightSensorCreator. The handler/service must go through a creator so all defaults live in one place. If the router built MoistureSensor itself, config would spread across the code and be hard to change.

5. Why type differs from device_type
type is a short key from the client. device_type is the stored value. They are different so the API stays simple while the domain owns the real name. The creator decides both device_type and default_config, not the client.

6. One devices table with role="sensor"
One table avoids duplicated columns and lets us filter by role. It prepares Phase 3, where actuators go in the same table with role="actuator".

7. Unknown type
It should return 400 with a clear message. The rejection happens in the registry, and the service/router turns that into 400. The router never builds a concrete class on its own.

## C. Compare, contrast, and scenarios

8. Factory Method vs simple factory
A simple factory is one function with if type == .... It is good enough when types rarely change and stay few. This phase still wants polymorphic creators so each type owns its own defaults and new types need no edit to shared code.

9. Factory Method vs Abstract Factory
Factory Method answers "which single object do I create?". Abstract Factory answers "which whole family of related objects do I create together?". Phase 2 only makes one sensor at a time, so Factory Method is enough.

10. Commits/parsing inside a creator
That is a trap because it mixes creation with persistence and HTTP. The creator would depend on SQLAlchemy or FastAPI and be hard to test. Persistence belongs in the repository, and HTTP belongs in the router; the creator only builds the domain object.
