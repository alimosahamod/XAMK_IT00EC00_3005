# Phase 4 — Answers

## A. Pattern

### 1. Intent of Builder

Builder puts a complex object together step by step and checks it only at the end. A location has a name and any number of zones, and the wizard sends them one after another. A big constructor would need all values at once and would grow with every new field. A half-filled dict written to the database is worse, because the bad row is already saved before anyone looks at it. Some rules also need the whole picture: a low threshold of 0.6 is fine alone, but wrong next to a high threshold of 0.3. So build() is the one place that checks everything and returns a valid product.

### 2. Participants

The product is LocationConfig with its Location and Zone objects. The builder is LocationConfigBuilder. A director is optional and we do not use one yet. The client is LocationConfigService, which calls the builder for the API. Before build() succeeds, the builder is not a finished product. It is just a bag of collected values and it may be incomplete. This matters because only the product may be saved or passed around. If the half-filled builder counted as a product, invalid data could travel through the system.

### 3. Rejected configurations in this lab

build() rejects an empty or blank location name, a configuration with no zones, a zone with an empty name, a threshold outside 0.0 to 1.0, and a low threshold that is not strictly lower than the high one. These rules belong in the domain because they are product rules, not HTTP rules. If they lived only in FastAPI, a second caller, a test, or a later CLI would bypass them. The HTTP layer would also become the place people must read to understand the product. Pydantic only checks the shape of the JSON; the domain checks the meaning.

## B. This phase of the application

### 4. The aggregate and the name

The builder produces one location together with all its zones. They form one unit: a zone alone has no meaning, and a location is only useful with its zones. The course uses location_id because the scope is a place, not only a greenhouse. A location can be a greenhouse, a lab bench room, or an outdoor bed, so the name still fits when the product grows. A single name across schema, DTOs, and UI also stops two names for the same thing from appearing. greenhouse_id does not exist in any table, endpoint, or DTO.

### 5. Path from request to database

The router receives BuildLocationConfigRequestDto. request_to_config turns it into builder calls: with_location_name, then one add_zone per zone, then build(). The service takes the returned LocationConfig and gives it to LocationRepository.save_config, which writes the rows. The saved rows are mapped back into LocationConfigDto. If build() raises ConfigurationError, nothing at all is persisted, because the repository is only called after build() returns. The router turns the error into a 400 with the message from the domain.

### 6. One transaction

The repository adds the location, calls flush() to get the id the database created, adds all zones, and commits once at the end. If the location committed on its own and a zone insert failed after that, the database would keep a location with no zones. Later code would read that location, find an empty zone list, and treat it as valid. That is a half-built aggregate: a row that exists but does not describe anything usable. One commit and a rollback on failure mean the location and its zones appear together or not at all.

### 7. The wizard and the Builder

The form collects the location name and a growing list of zones, which is the same stepwise collecting the builder does. But the React state is only input, not a product. On submit the UI sends one JSON request, and the builder in the backend does the real assembly and checking. The wizard repeats a few obvious checks, like low below high, so the user gets fast feedback. Those checks are a comfort feature. If the UI checks were removed, no invalid configuration could be saved, because the server still refuses it.

## C. Compare, contrast, and scenarios

### 8. Builder, Factory Method, Abstract Factory

Factory Method answers "which type?". One creator returns one finished object in one call, like a moisture sensor with its defaults. Abstract Factory answers "which matching kit?". One factory returns several objects that belong together, like the simulation device set, and picking the factory fixes the family for all of them. Builder answers "how do we assemble one valid whole in steps?". There is only one kind of product here, but it is built over many calls and can only be checked when all parts are there.

### 9. Fluent is not the pattern

Returning self from each method is only a coding style that makes the calls read nicely. Any class can do that without being a Builder. The pattern is the split between collecting and finishing: the builder is allowed to be incomplete while it collects, and build() is the gate that either produces a valid product or raises. A builder that checks nothing in build() is just a chained setter, and a builder with a normal, non-chained API is still a Builder.

### 10. The two traps

Putting the rules only in Pydantic ties them to one entry point. Any test, script, or later service that uses the builder directly would create invalid configurations, and the rules would live in the layer that should only speak HTTP. An empty build() also removes the single place where the whole configuration is judged. Mutating the builder after build() breaks the promise of immutability: the caller holds an object that looks checked, but its values have changed since the check. Here Location and Zone are frozen dataclasses and the zones are a tuple, so the product cannot be changed. A second build() is the correct way to get a second configuration.