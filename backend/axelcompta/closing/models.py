"""LiassePivot — modèle indépendant du format de sortie (doc 02 §5, doc 06 §6) :
la télédéclaration EDI est un renderer qu'on branche plus tard, pas une refonte.
Squelette de structure uniquement.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from axelcompta.core.ids import DossierId


@dataclass(frozen=True, slots=True)
class LiassePivot:
    """Sous-ensemble réduit pour la démo (doc 17 semaine 3) : bilan simplifié +
    compte de résultat + une case-clé 2065. La V1 couvre le jeu de formulaires
    complet.
    """

    dossier_id: DossierId
    exercice: str  # ex. "2026"
    cases: dict[str, int] = field(default_factory=dict)  # code case → centimes
