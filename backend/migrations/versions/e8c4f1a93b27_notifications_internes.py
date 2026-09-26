"""Notifications internes : état lu, lisibles par l'API.

Revision ID: e8c4f1a93b27
Revises: d7b2e4c81a05

Louis, 2026-09-26 : les notifications vivent dans l'application, plus dans
un e-mail. `lue_le` porte l'état de la cloche. L'API (rôle `axelcompta_web`)
lit la table et ne peut modifier que `lue_le` ; la policy par dossier est
déjà posée depuis `87fc7238e52e`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8c4f1a93b27"
down_revision: str | Sequence[str] | None = "d7b2e4c81a05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notifications_envoyees", sa.Column("lue_le", sa.DateTime(), nullable=True))
    op.execute("GRANT SELECT, UPDATE (lue_le) ON notifications_envoyees TO axelcompta_web")


def downgrade() -> None:
    op.execute("REVOKE SELECT, UPDATE ON notifications_envoyees FROM axelcompta_web")
    op.drop_column("notifications_envoyees", "lue_le")
