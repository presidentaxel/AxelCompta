"""LiassePivot — modèle indépendant du format de sortie (doc 02 §5, doc 06 §6) :
la télédéclaration EDI est un renderer qu'on branche plus tard, pas une refonte.
Squelette de structure uniquement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from axelcompta.core.identite import IdentiteEntreprise
from axelcompta.core.ids import DossierId


@dataclass(frozen=True, slots=True)
class LiassePivot:
    """Sous-ensemble réduit pour la démo (doc 17 semaine 3) : bilan simplifié +
    compte de résultat + une case-clé 2065. La V1 couvre le jeu de formulaires
    complet.

    `exercice_debut`/`exercice_fin` : les vraies bornes de l'exercice, dérivées
    des dates d'écriture réelles quand elles sont connues (un dossier réel
    peut avoir un exercice partiel — création en cours d'année — pas
    forcément aligné sur l'année civile). `None` si on ne les connaît pas
    (ex. `LiassePivot` construite à la main dans un test) — les renderers
    retombent alors sur l'année civile de `exercice`.
    """

    dossier_id: DossierId
    exercice: str  # ex. "2026"
    cases: dict[str, int] = field(default_factory=dict)  # code case → centimes
    exercice_debut: date | None = None
    exercice_fin: date | None = None
    # Renseignés seulement par une clôture avec `ParametresCloture` (liasse
    # fiscale complète, cases `2033A.xxx`, `2033B.xxx`... en plus des cases
    # historiques ci-dessus).
    identite: IdentiteEntreprise | None = None
    forme_juridique: str = ""


@dataclass(frozen=True, slots=True)
class ParametresCloture:
    """Ce que la clôture fiscale doit savoir du dossier, au-delà de ses
    écritures : bornes déclarées de l'exercice (pas les dates des écritures),
    identité pour les en-têtes, report des déficits de l'exercice précédent
    (2033-D ligne 870, en euros) et effectif salarié moyen (2033-E)."""

    exercice_debut: date
    exercice_fin: date
    forme_juridique: str
    identite: IdentiteEntreprise | None = None
    deficits_anterieurs: int = 0
    effectif_moyen: int = 0
