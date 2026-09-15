# Factory Method — Sensors

## Problem

We need to create different sensor types (moisture, light) with different
default configs. If every caller writes `MoistureSensor(...)` or a big
`if type == ...`, adding a new type means editing many places.

## Solution

An abstract `SensorCreator` declares one method `create_sensor()`. Each concrete
creator (`MoistureSensorCreator`, `LightSensorCreator`) builds its own sensor
with its own `device_type` and `default_config`. A small registry maps a short
type key (`"moisture"`, `"light"`) to the right creator. Callers only know the
key, not the concrete classes.

## Where to look in code

- `backend/src/domain/sensors/entity.py` — the `Sensor` product.
- `backend/src/domain/sensors/creators.py` — creators + `get_creator()` registry.
- `backend/src/application/sensors/service.py` — asks a creator, then saves.
- `backend/src/infrastructure/persistence/device_repository.py` — persistence.
- `backend/src/interfaces/api/sensors.py` — `GET` / `POST /api/sensors`.

## Extension exercise

Add a temperature sensor:

1. Add `TemperatureSensorCreator` in `creators.py` with
   `device_type="temperature_sensor"` and a config like `{"unit": "celsius"}`.
2. Register it: `"temperature": TemperatureSensorCreator()`.
3. Done — no router or service change needed.
