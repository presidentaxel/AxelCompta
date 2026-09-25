"""Règles de rappel et droits des membres d'une organisation.

Revision ID: c3f8a1d72e04
Revises: b4e1c8a72d09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3f8a1d72e04"
down_revision: str | Sequence[str] | None = "b4e1c8a72d09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "regles_rappel",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("libelle", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("canaux", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("rappels", sa.Column("regle_id", sa.String(), nullable=True))
    op.create_foreign_key("rappels_regle_id_fkey", "rappels", "regles_rappel", ["regle_id"], ["id"])
    op.create_table(
        "droits_membre",
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("tenant_id", "email"),
    )
    for table in ("regles_rappel", "droits_membre"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_isolation ON {table}
              FOR ALL TO axelcompta_web
              USING (tenant_id = current_setting('app.tenant_id', true))
              WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
            """
        )
    op.execute("GRANT SELECT, INSERT ON regles_rappel TO axelcompta_web")
    op.execute("GRANT SELECT, INSERT, UPDATE ON droits_membre TO axelcompta_web")


def downgrade() -> None:
    op.drop_constraint("rappels_regle_id_fkey", "rappels", type_="foreignkey")
    op.drop_column("rappels", "regle_id")
    for table in ("regles_rappel", "droits_membre"):
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {table}")
        op.execute(f"REVOKE ALL ON {table} FROM axelcompta_web")
        op.drop_table(table)
