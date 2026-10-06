# Phase 5 — Answers

## A. Pattern

### 1. Intent of Adapter

Adapter makes an existing interface fit the interface the client expects. If business code talks to a vendor protocol directly, it must know the odd field names, units, XML and status codes. Then every new vendor adds more if-branches and conversions to business code, and a change in the vendor format breaks the whole app. The adapter keeps all of this in one place.

### 2. Participants

The target or port is the interface the client wants, here SensorPort. The adaptee is the existing class with the wrong interface, here the vendor client. The adapter implements the port and calls the adaptee, here VendorStubSensorAdapter. The client uses only the port, here ReadingService. The adapter translates names, units, time formats and errors. It must not make business decisions, like when to water the plants.

### 3. Object adapter vs class adapter

Modern code prefers the object adapter. It holds the adaptee as a field (composition) instead of inheriting from it. This is more flexible: the adaptee can be swapped or mocked in tests, and the adapter does not inherit methods it should not expose. Many languages also do not support multiple inheritance well.

## B. This phase of the application

### 4. SensorPort and Reading

SensorPort is an abstract class in the domain with one method read(device). It returns a Reading with device_id, value, unit, source and recorded_at. The service depends on the port, so it does not care if the value comes from the simulation, a vendor SDK or real hardware later. A new adapter can be added without changing the service, and the service can be tested with a fake port.

### 5. Two adapters with different raw shapes

The simulation adapter creates the value directly in our format. The vendor stub returns a dict with sensorRef, val, uom in percent or kilolux, a time in epoch milliseconds and a status field. The different shape is the point, because translation is the job of an adapter. If both had the same shape, there would be nothing to adapt. Each adapter sets the source field (simulation or vendor), so every stored reading shows which adapter made it. The UI shows it as a badge.

### 6. Why append readings

If we only keep the latest value in memory, it is lost after a restart or refresh. If we overwrite one row, we lose the history and cannot see trends. Each read inserts a new row in sensor_readings, and the index on device_id and recorded_at DESC makes the latest value fast to find. Phase 6 Strategy uses the latest readings for its decisions. Phase 11 Observer and the charts in Phase 13 also use this history.

### 7. HTTP status and vendor types

A missing device returns 404, because the resource does not exist. An adapter error returns 400 with a detail message, for example a vendor error status or a device that is not a sensor. The router should never see vendor types. If it did, the vendor format would leak into the API and into the frontend. Then a vendor change would break the public API. The router only knows ReadingDto.

## C. Compare, contrast, and scenarios

### 8. Adapter vs Facade

Adapter changes the shape of one existing interface into the shape the client expects. Facade puts one simple interface in front of a whole subsystem, so it is easier to use. Adapter example: VendorStubSensorAdapter turns the vendor dict into a Reading. Facade example for Phase 7: one method like run_irrigation_check(zone) that loads readings, checks thresholds and starts the pump behind one call.

### 9. Adapter vs Decorator

Both wrap an object. An adapter gives the client a different interface than the wrapped object has. A decorator gives the client the same interface as the wrapped object and adds behavior, like logging or a safety check. In Phase 9, a decorator around SimulationActuatorAdapter is still an ActuatorPort.

### 10. Irrigation policy in the adapter

This is a trap because the adapter should only translate. If the rule is inside the vendor adapter, it only works for vendor devices and not for simulation devices. The same rule would have to be copied into every adapter. Changing the threshold would also mean changing infrastructure code. The decision belongs in the Strategy in Phase 6, which uses the zone thresholds per location_id. The adapter should only turn the raw value into a clean Reading.




I used the AI assistant Claude (and Claude Code) by Anthropic to help translate sentences from German to English, refine the phrasing, and write code for the individual steps.

