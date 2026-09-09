from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Feste Namensschemata fuer Indizes/Constraints. Ohne das wuerde Postgres
# automatische, teils kryptische Namen vergeben; damit sind Autogenerate-
# Migrationen stabil und reproduzierbar benannt, auch bei erneutem Generieren.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Gemeinsame Basisklasse fuer alle ORM-Modelle in infrastructure.persistence.

    Alembic vergleicht `Base.metadata` mit der echten DB (env.py).
    Jedes Modell (z.B. DeviceRow) muss von genau dieser Base erben -
    sonst taucht seine Tabelle nicht in Base.metadata auf.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
