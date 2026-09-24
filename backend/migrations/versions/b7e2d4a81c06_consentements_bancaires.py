"""consentements bancaires

Revision ID: b7e2d4a81c06
Revises: a91c4e2b7d10
Create Date: 2026-09-24 17:05:00.000000

État courant du consentement DSP2, lu par la synchro. SELECT pour le rôle
web (un écran pourra l'afficher plus tard) ; l'écriture reste au script
d'administration, propriétaire des tables.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b7e2d4a81c06"
down_revision: str | Sequence[str] | None = "a91c4e2b7d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consentements_bancaires",
        sa.Column("dossier_id", sa.String(), nullable=False),
        sa.Column("expire_le", sa.Date(), nullable=True),
        sa.Column("statut", sa.String(), nullable=False),
        sa.Column("releve_le", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"]),
        sa.PrimaryKeyConstraint("dossier_id"),
    )
    op.execute("ALTER TABLE consentements_bancaires ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY consentements_bancaires_isolation ON consentements_bancaires
          FOR ALL TO axelcompta_web
          USING (axelcompta_dossier_visible(dossier_id))
          WITH CHECK (axelcompta_dossier_visible(dossier_id))
        """
    )
    op.execute("GRANT SELECT ON consentements_bancaires TO axelcompta_web")


def downgrade() -> None:
    op.execute("REVOKE ALL ON consentements_bancaires FROM axelcompta_web")
    op.execute(
        "DROP POLICY IF EXISTS consentements_bancaires_isolation ON consentements_bancaires"
    )
    op.execute("ALTER TABLE consentements_bancaires DISABLE ROW LEVEL SECURITY")
    op.drop_table("consentements_bancaires")
