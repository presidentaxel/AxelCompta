"""Matching PlatformSettlement ↔ NormalizedTransaction (doc 13 §2.1, §4).

`reconcilier_bouchon` : version trivial pour la démo semaine 0 (doc 17) —
égalité exacte de montant, un seul candidat accepté. L'algorithme réel
(fenêtre de date ±3j/+5j, heuristique de libellé, tolérance 1 centime,
gestion des matchs multiples → revue humaine) est doc 13 §4.2, prévu
semaine 2.
"""

from __future__ import annotations

from .providers.base import NormalizedTransaction, PlatformSettlement


def reconcilier_bouchon(
    transactions: tuple[NormalizedTransaction, ...],
    settlements: tuple[PlatformSettlement, ...],
) -> tuple[tuple[NormalizedTransaction, PlatformSettlement], ...]:
    """Un settlement est apparié à LA transaction de montant strictement égal,
    si elle est unique. Pas de fenêtre de date, pas d'heuristique de libellé
    (doc 13 §4.2 — pour la vraie version). Les settlements sans match unique
    sont silencieusement ignorés à ce stade (pas d'état `en_attente_banque`
    ni de file de revue, doc 13 §4.3 — prévus semaine 2).
    """
    paires = []
    for settlement in settlements:
        candidates = [t for t in transactions if t.montant_cts == settlement.net_payout_cts]
        if len(candidates) == 1:
            paires.append((candidates[0], settlement))
    return tuple(paires)
