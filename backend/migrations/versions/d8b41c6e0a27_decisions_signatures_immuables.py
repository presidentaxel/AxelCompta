"""decisions et signatures immuables

Revision ID: d8b41c6e0a27
Revises: c2f91ab84e30
Create Date: 2026-09-24 17:10:00.000000

Même verrou que les écritures (a91c4e2b7d10) : une décision ou une
signature déjà enregistrée ne se modifie pas.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "d8b41c6e0a27"
down_revision: str | Sequence[str] | None = "c2f91ab84e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("decisions_humaines", "documents_signes")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_immuables
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION axelcompta_interdire_mutation()
            """
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immuables ON {table}")
