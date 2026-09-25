"""Portée et déclencheur automatique des règles de rappel.

Revision ID: d7b2e4c81a05
Revises: c3f8a1d72e04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7b2e4c81a05"
down_revision: str | Sequence[str] | None = "c3f8a1d72e04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "regles_rappel",
        sa.Column("portee", sa.String(), nullable=False, server_default="tous"),
    )
    op.add_column("regles_rappel", sa.Column("dossier_ids", sa.JSON(), nullable=True))
    op.add_column(
        "regles_rappel",
        sa.Column("declencheur", sa.String(), nullable=False, server_default="manuel"),
    )
    op.add_column("regles_rappel", sa.Column("jours_avant", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("regles_rappel", "jours_avant")
    op.drop_column("regles_rappel", "declencheur")
    op.drop_column("regles_rappel", "dossier_ids")
    op.drop_column("regles_rappel", "portee")
