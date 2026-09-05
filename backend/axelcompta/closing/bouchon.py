"""Clôture bouchon (doc 17 semaine 0) : balance triviale par compte à partir
du grand livre. Pas de distinction bilan/compte de résultat — ça viendra en
semaine 3 (doc 06 §5) une fois la couture prouvée.
"""

from __future__ import annotations

from axelcompta.core.ids import DossierId
from axelcompta.ledger.models import Ecriture, Sens
from axelcompta.ledger.service import LedgerService

from .models import LiassePivot
from .service import ClosingService


def _solde_par_compte(ecritures: tuple[Ecriture, ...]) -> dict[str, int]:
    balance: dict[str, int] = {}
    for ecriture in ecritures:
        for ligne in ecriture.lignes:
            signe = 1 if ligne.sens is Sens.DEBIT else -1
            balance[ligne.compte] = balance.get(ligne.compte, 0) + signe * ligne.montant.centimes
    return balance


class BouchonClosingService(ClosingService):
    def __init__(self, ledger: LedgerService) -> None:
        self._ledger = ledger

    def cloturer(self, dossier_id: DossierId, exercice: str) -> LiassePivot:
        ecritures = self._ledger.grand_livre(dossier_id)
        return LiassePivot(
            dossier_id=dossier_id, exercice=exercice, cases=_solde_par_compte(ecritures)
        )
