"""ecritures immuables

Revision ID: a91c4e2b7d10
Revises: f3a8c1d04e52
Create Date: 2026-09-24 16:45:00.000000

Invariant I2 (doc 06) : une écriture validée ne se modifie ni ne se
supprime. La correction est une contre-passation, pas un UPDATE.
Le trigger s'applique aussi au propriétaire des tables (scripts
d'admin), contrairement aux policies RLS.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "a91c4e2b7d10"
down_revision: str | Sequence[str] | None = "f3a8c1d04e52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION axelcompta_interdire_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION '% interdit sur % : écriture validée immuable', TG_OP, TG_TABLE_NAME
            USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    for table in ("ecritures", "lignes_ecriture"):
        op.execute(
            f"""
            CREATE TRIGGER {table}_immuables
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION axelcompta_interdire_mutation()
            """
        )


def downgrade() -> None:
    for table in ("lignes_ecriture", "ecritures"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immuables ON {table}")
    op.execute("DROP FUNCTION IF EXISTS axelcompta_interdire_mutation()")
