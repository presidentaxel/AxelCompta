"""Conventions génériques du Plan Comptable Général (doc 06 §2) — pas
spécifique à un pack métier, donc dans `core` plutôt que dans `packs`.
"""

from __future__ import annotations


def nature_depuis_compte(compte: str) -> str:
    """Convention PCG : classe 6 = charge, classe 7 = produit. Tout le reste
    (immobilisations, capital, tiers...) est hors scope démo."""
    if compte.startswith("6"):
        return "charge"
    if compte.startswith("7"):
        return "produit"
    return "autre"
