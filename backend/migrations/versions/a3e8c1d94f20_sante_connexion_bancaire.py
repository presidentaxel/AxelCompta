"""sante de connexion bancaire

Revision ID: a3e8c1d94f20
Revises: e4c7a9d25b13
Create Date: 2026-09-25 10:50:00.000000

Colonnes d'état courant sur consentements_bancaires. Pas une écriture :
on remplace le relevé précédent. SELECT déjà accordé au rôle web.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3e8c1d94f20"
down_revision: str | Sequence[str] | None = "e4c7a9d25b13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "consentements_bancaires",
        sa.Column("sante", sa.String(), nullable=False, server_default="jamais_connecte"),
    )
    op.add_column(
        "consentements_bancaires",
        sa.Column("en_pause", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "consentements_bancaires",
        sa.Column("acces_donnees", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "consentements_bancaires",
        sa.Column("dernier_rafraichissement", sa.DateTime(), nullable=True),
    )
    op.alter_column("consentements_bancaires", "sante", server_default=None)
    op.alter_column("consentements_bancaires", "en_pause", server_default=None)
    op.alter_column("consentements_bancaires", "acces_donnees", server_default=None)


def downgrade() -> None:
    op.drop_column("consentements_bancaires", "dernier_rafraichissement")
    op.drop_column("consentements_bancaires", "acces_donnees")
    op.drop_column("consentements_bancaires", "en_pause")
    op.drop_column("consentements_bancaires", "sante")
