"""Avenants de régime d'imposition, append-only.

Revision ID: a4d7e2c9b518
Revises: f1b6d3e82a47

Doc 06 §7 : un changement de régime (fin d'option IR, renonciation) est un
événement tracé qui prend effet à un exercice donné, jamais une réécriture.
Même verrou que les écritures et les décisions (`axelcompta_interdire_mutation`,
migration `a91c4e2b7d10`) : ni UPDATE ni DELETE, propriétaire compris.
Policy par dossier comme les autres tables dossier-scopées ; l'API ne fait
que lire, l'écriture passe par les tâches planifiées (rôle propriétaire).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4d7e2c9b518"
down_revision: str | Sequence[str] | None = "f1b6d3e82a47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "avenants_regime",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dossier_id", sa.String(), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("exercice_effet", sa.Integer(), nullable=False),
        sa.Column("regime_imposition", sa.String(), nullable=False),
        sa.Column("option_ir_debut", sa.Integer(), nullable=True),
        sa.Column("motif", sa.String(), nullable=False),
        sa.Column("enregistre_le", sa.DateTime(), nullable=False),
        sa.Column("enregistre_par", sa.String(), nullable=False),
    )
    op.create_index("ix_avenants_regime_dossier_id", "avenants_regime", ["dossier_id"])
    op.execute("ALTER TABLE avenants_regime ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY avenants_regime_isolation ON avenants_regime
          FOR ALL TO axelcompta_web
          USING (axelcompta_dossier_visible(dossier_id))
          WITH CHECK (axelcompta_dossier_visible(dossier_id))
        """
    )
    op.execute("GRANT SELECT ON avenants_regime TO axelcompta_web")
    op.execute(
        """
        CREATE TRIGGER avenants_regime_immuables
        BEFORE UPDATE OR DELETE ON avenants_regime
        FOR EACH ROW EXECUTE FUNCTION axelcompta_interdire_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS avenants_regime_immuables ON avenants_regime")
    op.drop_table("avenants_regime")
