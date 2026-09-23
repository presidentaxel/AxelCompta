"""dossiers : identite legale et fin d'exercice

Revision ID: b3d91e7a2c40
Revises: 87fc7238e52e
Create Date: 2026-09-23 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d91e7a2c40'
down_revision: Union[str, Sequence[str], None] = '87fc7238e52e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Les deux colonnes sont nullables : un dossier sans identité connue reste
    valide (dossier historique pseudonymisé, doc 07 §2.2), et une fin
    d'exercice absente vaut douze mois après le début (`Dossier.fin_exercice`).
    Les GRANT de la RLS (87fc7238e52e) portent sur la table, pas sur les
    colonnes : rien à ajouter côté `axelcompta_web`.
    """
    op.add_column('dossiers', sa.Column('exercice_fin', sa.Date(), nullable=True))
    op.add_column('dossiers', sa.Column('identite', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('dossiers', 'identite')
    op.drop_column('dossiers', 'exercice_fin')
