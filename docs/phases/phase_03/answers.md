# Phase 3 — Answers

## A. Pattern

### 1. Intent of Abstract Factory

Abstract Factory creates a whole group of related objects at once. The caller picks one factory and gets parts that fit together. If you pick each part on its own with a separate if, you can mix parts that do not belong together. The result looks complete but is broken.

### 2. Main participants

The abstract factory is the interface with one method per product group. A concrete factory builds one family. The abstract products are the common types. The concrete products are the real variants. The client only uses the abstract factory. Because the client chooses the factory once at the start, every product it gets after that comes from the same family. The client cannot mix families by accident.

### 3. When to use it and when to skip it

Use it when you have several products that must match, and several environments or variants of that set. Skip it when a request only needs one object, because then Factory Method is enough. Also skip it when mixing parts from different families is allowed, because then the extra structure only gets in the way.

## B. This phase of the application

### 4. Device family and create_device_set

A device family is one environment for the greenhouse, here simulation or edge. Calling create_device_set returns a list of four Device objects: a moisture sensor, a light sensor, a water pump and a grow light. All four carry the same family key and the same protocol. A simulation kit and an edge kit must not mix, because a simulated sensor and a real relay pin would not work together. The kit would then report values that no real device produced.

### 5. Composing the Phase 2 creators

The family factory does not build sensors itself. It asks get_creator for a moisture or light sensor, and then adds the family and the protocol to that result. So Factory Method still owns the sensor defaults, and Abstract Factory only decides which sensors belong in a kit. If the creators were deleted and everything was inlined, the sensor defaults would be copied into every family. Changing one threshold would mean editing each factory, and the families would drift apart over time.

### 6. Why one column instead of one table per family

A family is just a property of a device, not a different kind of thing. One column keeps one table, one repository and one query path, and lets us filter by family. A table per family would repeat every column and every index. The column has a server default of simulation, so old Phase 2 rows get a valid value. Without that backfill the column would be null for old rows, the not null rule would fail, and the old sensors would not load any more.

### 7. Filters and the old sensor routes

Provision returns four devices: two sensors and two actuators. The UI must send the family filter on every list request, otherwise the list shows simulation and edge devices together and the user cannot tell which kit is active. The Phase 2 sensor routes must keep working because the dashboard still has a Sensors section for Factory Method, and old clients still use them. Phase 3 adds a new API next to the old one instead of breaking it.

## C. Compare, contrast, and scenarios

### 8. Factory Method versus Abstract Factory

Factory Method asks which one product do I create. One creator returns one object, and each creator owns the defaults for its own type. Abstract Factory asks which product line do I create. One factory returns a set of objects that must be compatible, and choosing the factory fixes the family for all of them. The two work together rather than compete: Abstract Factory often uses Factory Method style methods inside, which is what happens here, because create_device_set calls the Phase 2 sensor creators and then tags their results with the family.

### 9. Building concrete devices in the handler

If a handler or a DTO builds simulation or edge devices directly, it has to repeat the family rules. Sooner or later one place is forgotten, and a kit gets a mixed protocol or a missing family key. That is the same consistency bug the pattern was added to remove. HTTP should only read the family name from the request, pass it to the service, and let the service ask get_family_factory. The router maps the result to DTOs and nothing else.

### 10. The god factory

Locations, readings and devices are not a family of matching products. They are not interchangeable and nobody needs a set of all three at once. One factory for all of them would only be a bag of unrelated functions, it would grow with every new entity, and it would need a reason to change for each of them. Abstract Factory is for product sets that vary together, so each group should keep its own creation code.
