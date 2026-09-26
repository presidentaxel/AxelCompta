"""Clôture de l'exercice par le chauffeur, depuis l'API.

Revision ID: c5f2a8d3e914
Revises: b8e3f5a1c762

Louis, 2026-09-26 : la clôture appartient au chauffeur, légalement
responsable de sa comptabilité ; le gestionnaire n'a aucun droit sur les
comptes. L'automatisation prépare et relance, le chauffeur valide, et on
doit pouvoir prouver qu'il l'a fait :
- `exercices_clos.attestation` garde le texte exact qu'il a accepté ;
- l'API (rôle `axelcompta_web`, soumis aux policies par dossier) reçoit les
  seuls droits d'écriture que la clôture demande : insérer les écritures
  d'inventaire et d'à-nouveaux, l'exercice clos, et ouvrir le dossier sur
  l'exercice suivant (colonnes de l'exercice et des régimes seulement).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5f2a8d3e914"
down_revision: str | Sequence[str] | None = "b8e3f5a1c762"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLONNES_OUVERTURE = (
    "exercice_debut, exercice_fin, regime_imposition, option_ir_debut, "
    "regime_tva, tva_recettes_regime"
)


def upgrade() -> None:
    op.add_column("exercices_clos", sa.Column("attestation", sa.Text(), nullable=True))
    op.execute("GRANT INSERT ON ecritures, lignes_ecriture, exercices_clos TO axelcompta_web")
    op.execute(f"GRANT UPDATE ({_COLONNES_OUVERTURE}) ON dossiers TO axelcompta_web")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE ({_COLONNES_OUVERTURE}) ON dossiers FROM axelcompta_web")
    op.execute("REVOKE INSERT ON ecritures, lignes_ecriture, exercices_clos FROM axelcompta_web")
    op.drop_column("exercices_clos", "attestation")
