from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from infrastructure.settings import settings
from interfaces.api.health import router as health_router

# 1. FastAPI App erstellen (Swagger & ReDoc deaktiviert)
app = FastAPI(
    title="Smart Greenhouse API",
    version="0.1.0",
    description="Backend API for the Smart Greenhouse monitoring system",
    docs_url=None,       # Deaktiviert /docs
    redoc_url=None,      # Deaktiviert /redoc
    openapi_url="/openapi.json",
)

# 2. CORS konfigurieren
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Router einbinden
app.include_router(health_router)


# 4. Discovery-Endpunkt auf GET /
@app.get("/", include_in_schema=False)
def root_discovery() -> dict[str, str]:
    return {
        "name": "Smart Greenhouse API",
        "description": "Welcome to the Smart Greenhouse API service",
        "docs_url": "/scalar",
        "openapi_url": "/openapi.json",
    }


# 5. Scalar API Reference auf GET /scalar
@app.get("/scalar", include_in_schema=False)
async def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Documentation",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )