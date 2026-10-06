# Adapter — Sensor readings

## Problem

Sensors do not all speak the same language. Our simulation gives a value in vwc or lux with a normal timestamp. The vendor SDK stub uses other field names (sensorRef, val, uom), sends moisture in percent and light in kilolux, gives the time as epoch milliseconds, and reports errors in a status field.

If the service or the router read these raw shapes directly, every new device type would add more if-branches and unit conversions to business code. The rest of the app would also depend on the vendor's format.

## Solution

The domain defines one port, SensorPort, with one method read(device) that returns a normalized Reading (device_id, value, unit, source, recorded_at).

Each source gets its own adapter that implements this port. SimulationSensorAdapter creates plausible values. VendorStubSensorAdapter calls the vendor client and translates its raw dict into a Reading: percent becomes a fraction, kilolux becomes lux, epoch milliseconds become a datetime with time zone, and a bad status becomes a SensorReadError.

The adapters only translate. They do not decide anything about watering. That decision comes later with Strategy.

The same idea is used for actuators. ActuatorPort has apply(device_id, command, payload). SimulationActuatorAdapter only stores the command in memory and logs it. There is no GPIO. Phase 9 will wrap this adapter with decorators.

## Selection rule

The adapter is chosen by the device family from Phase 3. A device with family simulation is read by SimulationSensorAdapter (source simulation). A device with family edge is read by VendorStubSensorAdapter (source vendor). Any other family, or a device that is not a sensor, raises a SensorReadError, so the API returns 400.

Only the selector in infrastructure/adapters/sensors/selector.py knows the concrete adapter classes. ReadingService gets the selector as a function and only works with SensorPort.

## Flow

POST /api/sensors/{id}/read loads the device (404 if it does not exist), selects the adapter, calls read(), inserts the reading into sensor_readings, and returns a ReadingDto. Every read inserts a new row, so the history grows. GET /api/sensors/{id}/readings?limit=1 returns the newest stored reading. The index on (device_id, recorded_at DESC) makes this fast.

## Where to look in code

backend/src/domain/sensors/ports.py has SensorPort.

backend/src/domain/sensors/reading.py has Reading.

backend/src/domain/sensors/errors.py has SensorReadError.

backend/src/domain/actuators/ports.py has ActuatorPort.

backend/src/infrastructure/adapters/sensors/simulation.py has the simulation adapter.

backend/src/infrastructure/adapters/sensors/vendor_stub.py has the vendor client stub (adaptee), the vendor adapter and the translation function.

backend/src/infrastructure/adapters/sensors/selector.py has the selection rule.

backend/src/infrastructure/adapters/actuators/simulation.py has SimulationActuatorAdapter.

backend/src/infrastructure/persistence/models.py has ReadingRow, and reading_repository.py stores and lists readings.

backend/src/application/readings/service.py has ReadingService.

backend/src/interfaces/api/sensors.py has the read and history endpoints.

frontend/src/features/sensors/SensorReadingPanel.tsx has the Read now button and the source badge.

## Extension exercise

Add a third vendor. Write a new class, for example AcmeSensorAdapter, that implements SensorPort and translates the Acme format into a Reading with source acme. Then add one entry to the dictionary in selector.py, for example the family acme. The service, the router, the database table and the DTO stay the same.
