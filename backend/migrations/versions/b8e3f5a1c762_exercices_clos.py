"""Historique des exercices clos, append-only.

Revision ID: b8e3f5a1c762
Revises: a4d7e2c9b518

Passage à l'exercice suivant (`axelcompta.exercices`) : une ligne par
exercice clos, jamais modifiée ni supprimée (même verrou que les écritures,
`axelcompta_interdire_mutation`). Policy par dossier ; l'API ne fait que lire.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8e3f5a1c762"
down_revision: str | Sequence[str] | None = "a4d7e2c9b518"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercices_clos",
        sa.Column("dossier_id", sa.String(), sa.ForeignKey("dossiers.id"), primary_key=True),
        sa.Column("debut", sa.Date(), primary_key=True),
        sa.Column("fin", sa.Date(), nullable=False),
        sa.Column("clos_le", sa.DateTime(), nullable=False),
        sa.Column("clos_par", sa.String(), nullable=False),
        sa.Column("changements", sa.JSON(), nullable=False),
    )
    op.execute("ALTER TABLE exercices_clos ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY exercices_clos_isolation ON exercices_clos
          FOR ALL TO axelcompta_web
          USING (axelcompta_dossier_visible(dossier_id))
          WITH CHECK (axelcompta_dossier_visible(dossier_id))
        """
    )
    op.execute("GRANT SELECT ON exercices_clos TO axelcompta_web")
    op.execute(
        """
        CREATE TRIGGER exercices_clos_immuables
        BEFORE UPDATE OR DELETE ON exercices_clos
        FOR EACH ROW EXECUTE FUNCTION axelcompta_interdire_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS exercices_clos_immuables ON exercices_clos")
    op.drop_table("exercices_clos")
