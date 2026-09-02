"""baseline

Revision ID: 001_baseline
Revises:
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

# Revision-Identifikatoren
revision: str = "001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 1: Keine Tabellen erstellen
    pass


def downgrade() -> None:
    # Phase 1: Keine Tabellen löschen
    pass