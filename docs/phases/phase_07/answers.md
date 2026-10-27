# Phase 7 — Answers

## 1. Intent of Facade

A facade gives one simple entry point to a group of classes, so the client does not need to know how they work together. If every handler or screen repeats the same steps over repositories and services, the same code exists in many places. When the order or a step changes, every copy has to be changed, and copies that get missed become bugs.

## 2. What a facade should not become

A facade should only call other parts and combine their results. It should not become a god object that holds all the business rules itself. Irrigation policy stays in the Strategy classes, sensor translation stays in the Adapters, and persistence stays in the repositories. Our facade only calls them and builds the DTO.

## 3. When to use it

Use Facade when a client needs several subsystems in a fixed order and many clients would repeat these steps. Skip it when one repository call is enough, because then the facade is just an extra layer. If the problem is that an interface does not match what the client expects, you need an Adapter, not a Facade.

## 4. The overview endpoint

It returns one LocationOverviewDto with the location (id and name), device_counts (sensor and actuator), latest_readings (device_id, value, unit, recorded_at), strategy_key and last_recommendation (action and reason). It is scoped by location_id because devices, zones and the automation rule all belong to a location, so the location is the natural unit for one snapshot.

## 5. No new table

The overview is only a read model. All data already exists: locations and zones from Phase 4, devices from Phases 2–3, sensor readings from Phase 5 and automation rules from Phase 6. The facade only reads and combines them. The recommendation is computed on each request, so it does not need to be stored either.

## 6. Handler calls only the facade

The handler stays small. It just calls get_overview() and turns a missing location into a 404. It does not need to know which repositories exist. Tests can check the whole overview with one request, or replace the facade with a fake. If the queries change later, for example a join or a view, only the facade or repositories change, and the router stays the same.

## 7. One fetch on the Overview page

If React made five calls, it would repeat the facade's work in the browser. The calls could also return data from different moments, need more requests, and every screen would have to copy the same logic. With one call, the backend gives one consistent snapshot. The facade reads the DB fresh on every GET and has no cache, so a new reading or a saved strategy shows up on the next load or refresh without extra frontend code.

## 8. Facade vs Adapter

An Adapter makes an existing interface usable. It translates one shape into the shape the client expects. A Facade makes a subsystem simpler to call by putting one method in front of many. In Phase 5 the sensor adapters translate vendor data (percent, kilolux, epoch milliseconds) into a normal Reading. In Phase 7 the LocationOverviewFacade combines repositories and the AutomationService behind get_overview().

## 9. N+1 queries

N+1 means one query to load all devices, then one more query per device to get its newest reading. With many devices this becomes many queries and gets slow. Our ReadingRepository solves this with one query using DISTINCT ON (device_id) ordered by recorded_at DESC, and the device counts come from one GROUP BY query. The SQL stays in the repository and the router has none.

## 10. Hiding every error

If every error becomes "overview failed", the client cannot react correctly. A missing location should be a 404 so the user can fix the id. A DB outage is a server error and should be logged and retried. A strategy error points to bad config. If they all look the same, debugging gets hard and the API is less honest. Our facade only turns "not ready yet" into a null recommendation and lets real errors through.

An AI Assistant (Claude by Anthropic) was used to understand the tasks clearly and formulate/translate the answers in english.  