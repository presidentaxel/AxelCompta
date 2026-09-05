"""Matching PlatformSettlement ↔ NormalizedTransaction (doc 13 §2.1, §4.2).

Algorithme réel (doc 17 semaine 2, remplace le bouchon de la semaine 0) :
montant à ±1 centime près, fenêtre de date [-3j, +5j] autour du
`payout_date` (délai de virement inter-banques), libellé contenant le nom
de la plateforme. Trois issues possibles par settlement (doc 13 §4.3) :
réconcilié (1 candidat), en attente banque (0 candidat), revue manuelle
(plusieurs candidats) — pas de file de revue construite pour la démo
(doc 17 §3), l'état est juste rapporté.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto

from .providers.base import NormalizedTransaction, PlatformSettlement

TOLERANCE_CENTIMES_PAR_DEFAUT = 1
JOURS_AVANT_PAR_DEFAUT = 3
JOURS_APRES_PAR_DEFAUT = 5


class EtatReconciliation(Enum):
    """doc 13 §4.3 (réduit : pas d'« écritures_générées »/« validé », qui
    dépendent de workflow, hors scope démo)."""

    RECONCILIE = auto()
    EN_ATTENTE_BANQUE = auto()
    REVUE_MANUELLE = auto()


@dataclass(frozen=True, slots=True)
class ResultatReconciliation:
    settlement: PlatformSettlement
    etat: EtatReconciliation
    transaction: NormalizedTransaction | None = None  # présente seulement si RECONCILIE


def _candidats(
    settlement: PlatformSettlement,
    transactions: tuple[NormalizedTransaction, ...],
    tolerance_centimes: int,
    jours_avant: int,
    jours_apres: int,
) -> list[NormalizedTransaction]:
    fenetre_debut = settlement.payout_date - timedelta(days=jours_avant)
    fenetre_fin = settlement.payout_date + timedelta(days=jours_apres)
    plateforme = settlement.platform.lower()
    return [
        transaction
        for transaction in transactions
        if abs(transaction.montant_cts - settlement.net_payout_cts) <= tolerance_centimes
        and fenetre_debut <= transaction.date <= fenetre_fin
        and plateforme in transaction.libelle.lower()
    ]


def reconcilier(
    transactions: tuple[NormalizedTransaction, ...],
    settlements: tuple[PlatformSettlement, ...],
    *,
    tolerance_centimes: int = TOLERANCE_CENTIMES_PAR_DEFAUT,
    jours_avant: int = JOURS_AVANT_PAR_DEFAUT,
    jours_apres: int = JOURS_APRES_PAR_DEFAUT,
) -> tuple[ResultatReconciliation, ...]:
    resultats = []
    for settlement in settlements:
        candidats = _candidats(
            settlement, transactions, tolerance_centimes, jours_avant, jours_apres
        )
        if len(candidats) == 1:
            resultats.append(
                ResultatReconciliation(settlement, EtatReconciliation.RECONCILIE, candidats[0])
            )
        elif len(candidats) == 0:
            resultats.append(
                ResultatReconciliation(settlement, EtatReconciliation.EN_ATTENTE_BANQUE)
            )
        else:
            resultats.append(ResultatReconciliation(settlement, EtatReconciliation.REVUE_MANUELLE))
    return tuple(resultats)
