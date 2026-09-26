"""Configuration de dossier de premier rang : pack métier et option IR.

Revision ID: f1b6d3e82a47
Revises: e8c4f1a93b27

Doc 06 §7, doc 12 §1.1. Les valeurs admises (forme, régimes) vivent dans la
matrice `tenants/matrice_statuts.toml`, validée par les repositories : pas
de contrainte CHECK en base, pour qu'un nouveau statut reste un ajout de
données et jamais une migration.

Remet aussi d'aplomb les dossiers dont la TVA des recettes est en franchise
mais le régime de TVA au réel : la franchise vaut pour les deux, la
validation refuserait désormais de les écrire.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1b6d3e82a47"
down_revision: str | Sequence[str] | None = "e8c4f1a93b27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dossiers",
        sa.Column("pack_metier", sa.String(), nullable=False, server_default="vtc"),
    )
    op.add_column("dossiers", sa.Column("option_ir_debut", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE dossiers SET regime_tva = 'franchise' "
        "WHERE tva_recettes_regime = 'franchise' AND regime_tva <> 'franchise'"
    )


def downgrade() -> None:
    op.drop_column("dossiers", "option_ir_debut")
    op.drop_column("dossiers", "pack_metier")
