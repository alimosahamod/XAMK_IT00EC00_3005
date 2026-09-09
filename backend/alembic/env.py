import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. src/ zum Python-Suchpfad hinzufügen, damit infrastructure.settings importiert werden kann
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from infrastructure.settings import settings

# 2. models importieren (nicht nur base!) - erst dadurch fuehrt Python die
# DeviceRow-Klasse aus und traegt die devices-Tabelle in Base.metadata ein.
# Ohne diesen Import waere Base.metadata leer und Autogenerate wuerde ein
# leeres upgrade() erzeugen.
from infrastructure.persistence import models

# Alembic Config-Objekt
config = context.config

# Logging-Konfiguration aus alembic.ini laden
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata zeigt jetzt auf die befuellte Base.metadata (devices-Tabelle)
target_metadata = models.Base.metadata

# Setze die sqlalchemy.url dynamisch aus unseren Settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Führt Migrationen im 'Offline'-Modus aus (generiert nur SQL-Skripte)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Führt Migrationen im 'Online'-Modus direkt gegen die Datenbank aus."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()