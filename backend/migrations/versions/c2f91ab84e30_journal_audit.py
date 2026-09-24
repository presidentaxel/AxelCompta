"""journal d'audit

Revision ID: c2f91ab84e30
Revises: b7e2d4a81c06
Create Date: 2026-09-24 17:20:00.000000

Trace append-only des décisions et des signatures. Même verrou que les
écritures (fonction déjà posée par a91c4e2b7d10).
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c2f91ab84e30"
down_revision: str | Sequence[str] | None = "b7e2d4a81c06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_audit",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("dossier_id", sa.String(), nullable=False),
        sa.Column("type_acte", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("acteur", sa.String(), nullable=False),
        sa.Column("acte_le", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_journal_audit_dossier_id"), "journal_audit", ["dossier_id"])
    op.execute("ALTER TABLE journal_audit ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY journal_audit_isolation ON journal_audit
          FOR ALL TO axelcompta_web
          USING (axelcompta_dossier_visible(dossier_id))
          WITH CHECK (axelcompta_dossier_visible(dossier_id))
        """
    )
    op.execute("GRANT SELECT, INSERT ON journal_audit TO axelcompta_web")
    op.execute(
        """
        CREATE TRIGGER journal_audit_immuable
        BEFORE UPDATE OR DELETE ON journal_audit
        FOR EACH ROW EXECUTE FUNCTION axelcompta_interdire_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS journal_audit_immuable ON journal_audit")
    op.execute("REVOKE ALL ON journal_audit FROM axelcompta_web")
    op.execute("DROP POLICY IF EXISTS journal_audit_isolation ON journal_audit")
    op.execute("ALTER TABLE journal_audit DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_journal_audit_dossier_id"), table_name="journal_audit")
    op.drop_table("journal_audit")
