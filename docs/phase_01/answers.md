# Phase 1 — Answers

## A. Pattern

**1. What is a design pattern?**
A design pattern is a way to solve a design problem. It is not ready code. It is also not a fixed rule. It is more like an idea you adapt to your own case.

**2. Three GoF families**
- **Creational**: about how objects get created (Factory Method).
- **Structural**: about how classes fit together into bigger parts.
- **Behavioral**: about how objects talk and share work (Strategy).

**3. When to skip a pattern**
Skip a pattern if the feature is small and probably won't grow. Adding a pattern too early just adds extra classes for no reason. That makes the code harder to read.

## B. This phase of the application

**4. Why an empty but running skeleton?**
Phase 1 has almost no business logic. The point is to check that frontend, backend, and database are connected first. "Empty but running" shows the wiring works. Unfinished classes would not show that, since nothing would run.

**5. The four backend layers**
- **domain**: business rules and models. No FastAPI or SQLAlchemy here.
- **application**: use cases that use the domain. No HTTP code here.
- **infrastructure**: technical stuff like DB connection and settings. No business rules here.
- **interfaces/api**: the HTTP routes. No direct DB queries here.

**6. GET /health and /scalar**
GET /health returns something like {"status": "ok", "db": "ok"}. It checks the database too, not just if the server is running, because the API could be up while the DB is down. /scalar is used for the API docs, and /docs is turned off because the project only wants one docs page instead of two.

**7. Why Alembic before any tables?**
Alembic is added early so every schema change is tracked from the start. If tables are created by hand first and migrations come later, the migration history is incomplete. Then it's hard to rebuild the same database somewhere else.

## C. Compare, contrast, and scenarios

**8. Dependency direction**
The flow goes: interfaces/api -> application -> domain. Infrastructure supports the other layers but domain doesnt depend on it. Domain can't import FastAPI, SQLAlchemy, or Pydantic, because that would tie the business logic to one framework and make it harder to test.

**9. Frontend can't show healthy badge**
First check simple stuff: is the backend running, is the frontend calling the right URL, is CORS or the proxy set up right, and does /health return the right JSON. This is a Phase 1 problem, not a pattern problem, since it's usually just wrong config, not design.

**10. What's still missing after Phase 1?**
After Phase 1 there is still no real logic, no tables, and no actual features yet. Later phases just add more code into the same layers (models, use cases, routes, migrations) without changing the base structure from this phase.
