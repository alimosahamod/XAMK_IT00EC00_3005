# Builder — Location configuration

## Problem

A location is not one simple value. It has a name and a list of zones, and every zone has a name, a low and a high moisture threshold, and an optional schedule. The user fills these fields step by step in the wizard, so the data arrives piece by piece.

A single large constructor would need every value at once, and it would grow each time a zone field is added. Writing a half-filled dictionary straight into the database is worse: the row is saved first and checked later, so a broken configuration is already stored.

The values also depend on each other. A low threshold of 0.6 is fine on its own, but not when the high threshold is 0.3. You can only judge the configuration when all parts are there.

## Solution

`LocationConfigBuilder` collects the parts. `with_location_name()` sets the name and `add_zone()` adds one zone. Both return the builder itself, so the calls can be chained. Nothing is checked yet, because the configuration is not finished.

`build()` is the only place that checks and the only way to get a product. It rejects an empty location name, a configuration without zones, an empty zone name, a threshold outside 0.0 to 1.0, and a low value that is not lower than the high value. If a rule is broken, it raises `ConfigurationError`. If everything is fine, it returns a `LocationConfig` with a frozen `Location` and a tuple of frozen `Zone` objects, so nobody can change the checked result afterwards.

## Where validation lives

The rules live in the domain builder, not in FastAPI and not in React. Pydantic only checks that the JSON has the right shape, for example that a threshold is a number. The question of whether the numbers make sense together is a business rule of this product.

The service calls `build()` before the repository. So if `build()` raises, the repository is never asked and nothing is written. The router catches `ConfigurationError` and turns it into a 400 with the message from the domain. The wizard repeats a few obvious checks to give fast feedback, but it is a comfort feature, not the source of truth.

## One transaction

`LocationRepository.save_config()` adds the location, calls `flush()` to get the id the database created, then adds all zones and commits once at the end. If a zone insert fails, the rollback also removes the location. The database never holds a location without its zones.

## Why `location_id`

The product is a smart greenhouse, but the relational scope is called location. A location can be a greenhouse, a lab bench room, or an outdoor bed, so the name stays true when the product grows. Every zone row carries `location_id`, and later phases keep using it as the top-level key. The name `greenhouse_id` does not appear in any table, endpoint, or DTO.

## Contrast with Factory Method and Abstract Factory

Factory Method answers "which type do I create?". One creator returns one finished object in one call, like a moisture sensor with its defaults.

Abstract Factory answers "which matching set do I create?". One factory returns several objects that belong together, like the simulation device kit.

Builder answers "how do I assemble one valid whole in steps?". There is only one kind of product here, a location configuration, but it is put together over many calls and can only be checked at the end.

## Fluent is not Builder

`builder.add_zone(...).build()` reads nicely because each method returns `self`. That is only a coding style. The pattern is the split between collecting and finishing: the builder is allowed to be incomplete, and `build()` is the gate that either produces a valid product or raises.

## Where to look in code

`backend/src/domain/locations/entity.py` has `Location`, `Zone` and `LocationConfig`.

`backend/src/domain/locations/config_builder.py` has the builder and all rules.

`backend/src/domain/locations/errors.py` has `ConfigurationError`.

`backend/src/application/locations/dto.py` has the request and response models.

`backend/src/application/locations/mappers.py` turns the request into builder calls and the saved rows into DTOs.

`backend/src/application/locations/config_service.py` builds first and saves second.

`backend/src/infrastructure/persistence/models.py` has `LocationRow` and `ZoneRow`.

`backend/src/infrastructure/persistence/location_repository.py` has the one-commit save and the read by id.

`backend/src/interfaces/api/locations.py` has `POST /api/locations/config` and `GET /api/locations/{location_id}/config`.

`frontend/src/components/config/LocationConfigWizard.tsx` has the wizard.

## Extension exercise

Add a director. A `DefaultLocationDirector` could take the builder and produce a standard two-zone starter location, so the client does not repeat the same calls. The builder keeps the rules, the director only knows the recipe.
