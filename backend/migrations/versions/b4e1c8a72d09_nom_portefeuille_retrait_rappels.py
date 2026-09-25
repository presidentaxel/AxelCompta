"""Nom du portefeuille modifiable, retrait d'un dossier, rappels.

Revision ID: b4e1c8a72d09
Revises: a3e8c1d94f20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4e1c8a72d09"
down_revision: str | Sequence[str] | None = "a3e8c1d94f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dossiers", sa.Column("retire_le", sa.Date(), nullable=True))
    op.create_table(
        "rappels",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("dossier_id", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("canal", sa.String(), nullable=False),
        sa.Column("cree_le", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("GRANT UPDATE (nom) ON tenants TO axelcompta_web")
    op.execute("GRANT UPDATE (retire_le) ON dossiers TO axelcompta_web")
    op.execute("ALTER TABLE rappels ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY rappels_isolation ON rappels
          FOR ALL TO axelcompta_web
          USING (tenant_id = current_setting('app.tenant_id', true))
          WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
        """
    )
    op.execute("GRANT SELECT, INSERT ON rappels TO axelcompta_web")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rappels_isolation ON rappels")
    op.execute("REVOKE ALL ON rappels FROM axelcompta_web")
    op.drop_table("rappels")
    op.execute("REVOKE UPDATE (nom) ON tenants FROM axelcompta_web")
    op.execute("REVOKE UPDATE (retire_le) ON dossiers FROM axelcompta_web")
    op.drop_column("dossiers", "retire_le")
