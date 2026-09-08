# Smart Greenhouse

A three-tier smart-greenhouse monitoring system: a **FastAPI** backend, **PostgreSQL** with **Alembic** migrations, and a **Vite + React + TypeScript + Tailwind** frontend. This repository is built up phase by phase; Phase 1 is the runnable skeleton with no business tables yet.

## Prerequisites

| Tool | Minimum version |
|------|-----------------|
| Python | 3.11+ |
| Node.js | 20 LTS |
| Docker Desktop | current |
| Git | any |

## First-time setup

```bash
# 1. Environment
cp .env.example .env                 # root: DB credentials, DATABASE_URL, API host/port, CORS
cp frontend/.env.example frontend/.env.local   # optional: VITE_API_BASE_URL

# 2. Database (PostgreSQL 16 via Docker Compose)
docker compose up -d
docker compose ps                    # wait until postgres is "healthy"

# 3. Backend (from backend/)
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 4. Apply the Alembic baseline (creates alembic_version only, no business tables)
alembic upgrade head
alembic current                      # should point at 001_baseline

# 5. Frontend (from frontend/)
cd ../frontend
npm install
```

## Daily start

Run each in its own terminal:

```bash
# Database
docker compose up -d

# Backend  (from backend/, venv active)
cd backend/src && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (from frontend/)
cd frontend && npm run dev
```

> **Note:** start Uvicorn from `backend/src/` so the `infrastructure` / `interfaces` packages import correctly.

## URLs

| What | URL |
|------|-----|
| API root (discovery) | http://localhost:8000/ |
| Health check | http://localhost:8000/health |
| Scalar API reference | http://localhost:8000/scalar |
| OpenAPI schema | http://localhost:8000/openapi.json |
| Web UI | http://localhost:5173/ |
| Dashboard | http://localhost:5173/dashboard |

Swagger `/docs` and ReDoc `/redoc` are intentionally disabled; use Scalar instead.

## Quality tooling (optional)

```bash
cd backend
ruff check . && ruff format --check .
PYTHONPATH=src pytest
```

## Phase order

See [docs/phases/README.md](docs/phases/README.md) for the full phase sequence. Phase 2 (Factory Method) adds the `devices` table, sensor creators, `/api/sensors`, and fills the **Sensors** dashboard section.
