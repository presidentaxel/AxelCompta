"""Mode de relance des connexions bancaires, par portefeuille et par dossier.

Revision ID: e2b9d7c41f05
Revises: d6a9c4e17b83

Doc 14 §2.3 : en « auto », AxeLCompta prévient le chauffeur dans
l'application (J-14, J-7, à l'expiration puis tous les 3 jours) ; en
« manuel », seul le gestionnaire est prévenu. Un dossier peut suivre le
portefeuille (NULL) ou avoir son propre mode. L'API ne peut modifier que ces
deux colonnes, comme le nom du portefeuille.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2b9d7c41f05"
down_revision: str | Sequence[str] | None = "d6a9c4e17b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("relance_consentement", sa.String(), nullable=False, server_default="auto"),
    )
    op.add_column("dossiers", sa.Column("relance_consentement", sa.String(), nullable=True))
    op.create_check_constraint(
        "tenants_relance_consentement_valide",
        "tenants",
        "relance_consentement IN ('auto', 'manuel')",
    )
    op.create_check_constraint(
        "dossiers_relance_consentement_valide",
        "dossiers",
        "relance_consentement IS NULL OR relance_consentement IN ('auto', 'manuel')",
    )
    op.execute("GRANT UPDATE (relance_consentement) ON tenants TO axelcompta_web")
    op.execute("GRANT UPDATE (relance_consentement) ON dossiers TO axelcompta_web")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (relance_consentement) ON dossiers FROM axelcompta_web")
    op.execute("REVOKE UPDATE (relance_consentement) ON tenants FROM axelcompta_web")
    op.drop_constraint("dossiers_relance_consentement_valide", "dossiers")
    op.drop_constraint("tenants_relance_consentement_valide", "tenants")
    op.drop_column("dossiers", "relance_consentement")
    op.drop_column("tenants", "relance_consentement")
