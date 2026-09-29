# Abstract Factory — Device families

## Problem

A greenhouse works in different places. During development, all parts run in a simulation. On real hardware, the parts connect to real pins. Each place needs a full set of parts that match. This set has two sensors for water and light, and two tools to add water and light.

If you choose each part one by one with an if-statement, you can make mistakes. You might get a real sensor and a simulated pump together. The kit looks complete, but the parts do not work together.

## Solution

A base factory called DeviceFamilyFactory sets a family_key and a method called create_device_set(). Each real factory builds a full kit where all parts match:

SimulationDeviceFactory uses the family name simulation, the protocol sim, simulation names, and settings like flow rate.

EdgeHardwareFactory uses the family name edge, the protocol gpio-stub, hardware names, and settings like pin numbers.

The function get_family_factory(family) picks the right factory from the family name. The rest of the code does not need to know the exact class name. If a family name does not exist, the code stops and sends a 400 error.

The older sensor tools are reused, not replaced. The family factory asks for a base sensor and adds the family name and protocol to it. This keeps the basic sensor settings in one place.

## Contrast with Factory Method

Factory Method answers the question: which single item do you want? It uses one tool to make one item in one call. It makes one sensor per request.

Abstract Factory answers the question: which group of items do you want? It uses one factory to make several items that work together. When you pick the factory once, all items in the kit use the same family.

An Abstract Factory often uses simple Factory Methods inside itself. That is what happens here: the method create_device_set() calls the sensor creators to build each piece.

## Where to look in code

backend/src/domain/devices/entity.py contains the shared Device model for sensors and tools.

backend/src/domain/devices/family_factory.py contains the base factory, both real factories, and the function get_family_factory().

backend/src/domain/sensors/creators.py contains the sensor makers that are still used.

backend/src/application/devices/family_service.py finds the right factory and saves the full kit.

backend/src/application/devices/dto.py and mappers.py contain the data format for the web API and the translation code.

backend/src/infrastructure/persistence/models.py contains the database setup with the family column.

backend/src/infrastructure/persistence/device_repository.py handles saving and loading the devices.

backend/src/interfaces/api/devices.py contains the web routes to get and create devices.

frontend/src/components/devices/ contains the web screen to switch families and see the list.

## Why Device is not a DTO

Device is a pure data object for the core program. It does not know about web frameworks or database tools. Because of this, the factory and database code can use it easily without extra rules. DeviceDto is only for sending data over the web.

Keeping them separate protects the system. If you change a name in the core program, the web output does not break. The translation code stays in one file instead of being spread out. The factory and the database never need to use DeviceDto.

## Extension exercise

You can add a third family, like lab.

First, add LabDeviceFactory inside family_factory.py with the family key lab, a new protocol, and new settings.

Second, add lab: LabDeviceFactory() to the factory list called _FACTORIES.

Third, add the word lab to the type list in frontend/src/services/api.ts.

You do not need to change the service, database, web router, or database tables.