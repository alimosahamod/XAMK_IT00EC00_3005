from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ermittelt den Pfad zur .env-Datei im Projekt-Root (zwei Ordner über src/)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # Felder mit Default-Werten als Fallback
    database_url: str = "postgresql+psycopg://greenhouse:greenhouse@localhost:5432/greenhouse"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # Konfiguration: Wo liegt die .env-Datei und wie soll sie gelesen werden?
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"  # Ignoriert zusätzliche Variablen in der .env, die hier nicht definiert sind
    )

# Globale Instanz zum Importieren in anderen Modulen
settings = Settings()