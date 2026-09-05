"""ProposedEntry — sortie du pipeline de catégorisation, avant validation par
`workflow` et écriture réelle via `ledger` (doc 03 §3, doc 05).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from axelcompta.core.ids import DossierId, TransactionId


class Etage(Enum):
    """Quel étage du pipeline a produit la proposition (doc 05 §1)."""

    REGLE = auto()
    ML = auto()
    LLM = auto()
    REVUE_HUMAINE = auto()


@dataclass(frozen=True, slots=True)
class ProposedEntry:
    """Une catégorisation proposée pour une transaction, pas encore une écriture.

    À faire (hors squelette) : le template d'écriture réel se construit à
    partir de `categorie` + le pack du dossier (doc 06 §3) — pas ici.
    """

    dossier_id: DossierId
    transaction_id: TransactionId
    categorie: str
    etage: Etage
    confiance: float  # [0.0, 1.0]
