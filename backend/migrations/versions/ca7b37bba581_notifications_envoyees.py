"""notifications envoyees

Revision ID: ca7b37bba581
Revises: 7cd5053e8209
Create Date: 2026-09-22 00:23:42.878758

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca7b37bba581'
down_revision: Union[str, Sequence[str], None] = '7cd5053e8209'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('notifications_envoyees',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('dossier_id', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('envoye_le', sa.DateTime(), nullable=False),
    sa.Column('ecriture_ids', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['dossier_id'], ['dossiers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_envoyees_dossier_id'), 'notifications_envoyees', ['dossier_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_notifications_envoyees_dossier_id'), table_name='notifications_envoyees')
    op.drop_table('notifications_envoyees')
