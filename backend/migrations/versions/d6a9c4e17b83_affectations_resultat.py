"""Décisions d'affectation du résultat, append-only.

Revision ID: d6a9c4e17b83
Revises: c5f2a8d3e914

Louis, 2026-09-26 : le chauffeur choisit seul ce qu'il fait de son résultat
(réserves, dividendes), sur un écran à lui. Une ligne par exercice clos,
jamais modifiée (même verrou que les écritures), policy par dossier ; l'API
lit et insère, sous l'identité du chauffeur.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6a9c4e17b83"
down_revision: str | Sequence[str] | None = "c5f2a8d3e914"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "affectations_resultat",
        sa.Column("dossier_id", sa.String(), sa.ForeignKey("dossiers.id"), primary_key=True),
        sa.Column("annee_exercice", sa.Integer(), primary_key=True),
        sa.Column("scenario", sa.String(), nullable=False),
        sa.Column("dividendes_cts", sa.Integer(), nullable=False),
        sa.Column("reserve_legale_cts", sa.Integer(), nullable=False),
        sa.Column("decide_le", sa.DateTime(), nullable=False),
        sa.Column("decide_par", sa.String(), nullable=False),
    )
    op.execute("ALTER TABLE affectations_resultat ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY affectations_resultat_isolation ON affectations_resultat
          FOR ALL TO axelcompta_web
          USING (axelcompta_dossier_visible(dossier_id))
          WITH CHECK (axelcompta_dossier_visible(dossier_id))
        """
    )
    op.execute("GRANT SELECT, INSERT ON affectations_resultat TO axelcompta_web")
    op.execute(
        """
        CREATE TRIGGER affectations_resultat_immuables
        BEFORE UPDATE OR DELETE ON affectations_resultat
        FOR EACH ROW EXECUTE FUNCTION axelcompta_interdire_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS affectations_resultat_immuables ON affectations_resultat")
    op.drop_table("affectations_resultat")
