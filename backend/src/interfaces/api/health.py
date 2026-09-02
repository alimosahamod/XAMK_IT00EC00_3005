from fastapi import APIRouter
from infrastructure.db import check_db_connection

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "fail",
    }