"""documents signes

Revision ID: f3a8c1d04e52
Revises: b3d91e7a2c40
Create Date: 2026-09-24 12:20:00.000000

Preuve de signature append-only. Isolation identique aux autres tables
par dossier : policy `axelcompta_dossier_visible`, GRANT SELECT + INSERT
pour `axelcompta_web` (la route de signature écrit, le résumé lit).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a8c1d04e52"
down_revision: Union[str, Sequence[str], None] = "b3d91e7a2c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents_signes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("dossier_id", sa.String(), nullable=False),
        sa.Column("type_document", sa.String(), nullable=False),
        sa.Column("contenu_pdf", sa.LargeBinary(), nullable=False),
        sa.Column("signataire", sa.String(), nullable=False),
        sa.Column("signe_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("qualifie", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_documents_signes_dossier_id"), "documents_signes", ["dossier_id"], unique=False
    )
    op.execute("ALTER TABLE documents_signes ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY documents_signes_isolation ON documents_signes
          FOR ALL TO axelcompta_web
          USING (axelcompta_dossier_visible(dossier_id))
          WITH CHECK (axelcompta_dossier_visible(dossier_id))
        """
    )
    op.execute("GRANT SELECT, INSERT ON documents_signes TO axelcompta_web")


def downgrade() -> None:
    op.execute("REVOKE ALL ON documents_signes FROM axelcompta_web")
    op.execute("DROP POLICY IF EXISTS documents_signes_isolation ON documents_signes")
    op.execute("ALTER TABLE documents_signes DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_documents_signes_dossier_id"), table_name="documents_signes")
    op.drop_table("documents_signes")
