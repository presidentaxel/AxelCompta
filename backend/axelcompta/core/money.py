"""Money — montants en centimes entiers.

Invariant absolu (doc 06 §1, doc 08 §2.3) : les flottants sont interdits pour
l'argent. Toute arithmétique (addition, ventilation TVA...) reste à écrire —
squelette de structure uniquement, aucune méthode encore implémentée.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Money:
    """Un montant en centimes (int), toujours dans une devise donnée.

    À faire (hors squelette) : addition/soustraction sûres, ventilation au
    centime près (répartition d'un total entre plusieurs lignes sans perte
    ni double-comptage), formatage.
    """

    centimes: int
    devise: str = "EUR"
