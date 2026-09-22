"""cles etrangeres decisions, propositions, journal ingestion

Revision ID: 7cd5053e8209
Revises: a016d1659a6e
Create Date: 2026-09-22 00:18:54.842910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cd5053e8209'
down_revision: Union[str, Sequence[str], None] = 'a016d1659a6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Pose les clés étrangères vers `dossiers` et `ecritures`, qui manquaient
    tant que ces tables n'étaient jamais peuplées (elles le sont depuis
    `demo_seed` et la synchro Digifactory). Échoue, avec le nom de la
    contrainte violée, si une décision, une annotation, une proposition ou
    une entrée du journal pointe vers un dossier ou une écriture qui
    n'existe pas : ces lignes sont à corriger à la main, pas à supprimer en
    silence. `propositions_categorisation.ecriture_id` n'a volontairement pas
    de FK (voir `workflow/orm.py`).
    """
    op.create_foreign_key(
        'annotations_dev_ecriture_id_fkey', 'annotations_dev', 'ecritures', ['ecriture_id'], ['id']
    )
    op.create_foreign_key(
        'annotations_dev_dossier_id_fkey', 'annotations_dev', 'dossiers', ['dossier_id'], ['id']
    )
    op.create_foreign_key(
        'curseurs_synchro_dossier_id_fkey', 'curseurs_synchro', 'dossiers', ['dossier_id'], ['id']
    )
    op.create_foreign_key(
        'decisions_humaines_ecriture_id_fkey', 'decisions_humaines', 'ecritures', ['ecriture_id'], ['id']
    )
    op.create_foreign_key(
        'decisions_humaines_dossier_id_fkey', 'decisions_humaines', 'dossiers', ['dossier_id'], ['id']
    )
    op.create_foreign_key(
        'ingestion_brut_dossier_id_fkey', 'ingestion_brut', 'dossiers', ['dossier_id'], ['id']
    )
    op.create_foreign_key(
        'propositions_categorisation_dossier_id_fkey', 'propositions_categorisation', 'dossiers', ['dossier_id'], ['id']
    )
    op.create_foreign_key(
        'quarantaine_ingestion_dossier_id_fkey', 'quarantaine_ingestion', 'dossiers', ['dossier_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('quarantaine_ingestion_dossier_id_fkey', 'quarantaine_ingestion', type_='foreignkey')
    op.drop_constraint('propositions_categorisation_dossier_id_fkey', 'propositions_categorisation', type_='foreignkey')
    op.drop_constraint('ingestion_brut_dossier_id_fkey', 'ingestion_brut', type_='foreignkey')
    op.drop_constraint('decisions_humaines_dossier_id_fkey', 'decisions_humaines', type_='foreignkey')
    op.drop_constraint('decisions_humaines_ecriture_id_fkey', 'decisions_humaines', type_='foreignkey')
    op.drop_constraint('curseurs_synchro_dossier_id_fkey', 'curseurs_synchro', type_='foreignkey')
    op.drop_constraint('annotations_dev_dossier_id_fkey', 'annotations_dev', type_='foreignkey')
    op.drop_constraint('annotations_dev_ecriture_id_fkey', 'annotations_dev', type_='foreignkey')
