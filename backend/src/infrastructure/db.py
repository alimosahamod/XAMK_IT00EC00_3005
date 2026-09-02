import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.settings import settings

logger = logging.getLogger(__name__)

# Erstellt die SQLAlchemy-Engine mit der konfigurierten URL
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Prüft Verbindungen vor der Verwendung auf Gültigkeit
)


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