import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.settings import settings

logger = logging.getLogger(__name__)

# Erstellt die SQLAlchemy-Engine mit der konfigurierten URL
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Prüft Verbindungen vor der Verwendung auf Gültigkeit
)

# Session-Factory: erzeugt pro Aufruf eine neue, unabhaengige Session-Instanz,
# gebunden an unsere engine. autocommit/autoflush=False, damit Commits explizit
# im Repository/Service passieren (kein "magisches" Auto-Commit).
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def check_db_connection() -> bool:
    """Führt 'SELECT 1' aus, um die Erreichbarkeit der Datenbank zu prüfen.

    Returns:
        True, wenn die Abfrage erfolgreich war, andernfalls False.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("Datenbankverbindung fehlgeschlagen: %s", exc)
        return False


def get_db() -> Generator[Session, None, None]:
    """FastAPI-Dependency: liefert eine Session pro Request und schliesst sie danach.

    Verwendung: `db: Session = Depends(get_db)` im Router/Repository.
    Der `yield` haelt die Session waehrend des Requests offen; das `finally`
    stellt sicher, dass sie auch bei einer Exception im Handler geschlossen wird.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()