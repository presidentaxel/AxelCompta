"""Contre-passation d'une écriture déjà validée (doc 06 §1).

L'originale n'est jamais modifiée. L'inverse a les mêmes comptes et les
mêmes montants, le sens opposé, un identifiant stable pour rester
idempotente.
"""

from __future__ import annotations

from axelcompta.core.ids import EcritureId

from .models import Ecriture, Journal, LigneEcriture, Sens


def _sens_oppose(sens: Sens) -> Sens:
    return Sens.CREDIT if sens is Sens.DEBIT else Sens.DEBIT


def contrepasser(ecriture: Ecriture) -> Ecriture:
    return Ecriture(
        id=EcritureId(f"{ecriture.id}:contrepassation"),
        dossier_id=ecriture.dossier_id,
        journal=Journal.OD,
        date=ecriture.date,
        libelle=f"Contre-passation {ecriture.libelle}",
        reference_piece=str(ecriture.id),
        lignes=tuple(
            LigneEcriture(
                compte=ligne.compte,
                sens=_sens_oppose(ligne.sens),
                montant=ligne.montant,
                analytique=ligne.analytique,
                code_tva=ligne.code_tva,
            )
            for ligne in ecriture.lignes
        ),
    )
