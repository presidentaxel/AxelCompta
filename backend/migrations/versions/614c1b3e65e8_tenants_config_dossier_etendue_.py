"""tenants, config dossier etendue, propositions categorisation

Revision ID: 614c1b3e65e8
Revises: 55cf8c93e5bf
Create Date: 2026-09-21 23:55:49.163626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '614c1b3e65e8'
down_revision: Union[str, Sequence[str], None] = '55cf8c93e5bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Les nouvelles colonnes de `dossiers` sont NOT NULL sans valeur par
    défaut : la table n'a jamais été peuplée (les dossiers de démo étaient
    recalculés en mémoire, doc 17), et inventer une config comptable
    (régime TVA, exercice) pour d'éventuelles lignes existantes serait pire
    qu'échouer. Si elle contient des lignes, on s'arrête avec un message clair.
    """
    if op.get_bind().execute(sa.text("SELECT count(*) FROM dossiers")).scalar():
        raise RuntimeError(
            "dossiers n'est pas vide : compléter la config de chaque dossier "
            "(nom, régime TVA recettes, début d'exercice...) avant cette migration."
        )
    op.create_table('propositions_categorisation',
    sa.Column('ecriture_id', sa.String(), nullable=False),
    sa.Column('dossier_id', sa.String(), nullable=False),
    sa.Column('categorie', sa.String(), nullable=False),
    sa.Column('etage', sa.String(), nullable=False),
    sa.Column('confiance', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('ecriture_id')
    )
    op.create_table('tenants',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('nom', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('dossiers', sa.Column('nom', sa.String(), nullable=False))
    op.add_column('dossiers', sa.Column('tva_recettes_regime', sa.String(), nullable=False))
    op.add_column('dossiers', sa.Column('exercice_debut', sa.Date(), nullable=False))
    op.add_column('dossiers', sa.Column('plateformes', sa.JSON(), nullable=False))
    op.add_column('dossiers', sa.Column('mode_acces_bancaire', sa.String(), nullable=False))
    op.add_column('dossiers', sa.Column('contact_nr', sa.String(), nullable=True))
    op.create_unique_constraint('dossiers_contact_nr_key', 'dossiers', ['contact_nr'])
    op.create_foreign_key('dossiers_tenant_id_fkey', 'dossiers', 'tenants', ['tenant_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('dossiers_tenant_id_fkey', 'dossiers', type_='foreignkey')
    op.drop_constraint('dossiers_contact_nr_key', 'dossiers', type_='unique')
    op.drop_column('dossiers', 'contact_nr')
    op.drop_column('dossiers', 'mode_acces_bancaire')
    op.drop_column('dossiers', 'plateformes')
    op.drop_column('dossiers', 'exercice_debut')
    op.drop_column('dossiers', 'tva_recettes_regime')
    op.drop_column('dossiers', 'nom')
    op.drop_table('tenants')
    op.drop_table('propositions_categorisation')
