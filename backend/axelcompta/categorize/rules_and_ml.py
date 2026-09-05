"""RulesAndMlPipeline — implémentation concrète pour la démo (doc 17 §3) :
étage 1 (règles) puis étage 2 (ML), pas de LLM ni de revue humaine.
"""

from __future__ import annotations

from dataclasses import dataclass

from axelcompta.core.ids import DossierId
from axelcompta.ingestion.providers.base import NormalizedTransaction
from axelcompta.packs.vtc_demo import RegleCategorisation

from .ml_fallback import ModeleSklearn, predire
from .models import Etage, ProposedEntry
from .pipeline import CategorizationPipeline

CONFIANCE_PAR_NIVEAU = {"haute": 0.95, "moyenne": 0.75, "basse": 0.5}
CATEGORIE_PAR_DEFAUT = "non_categorise_a_verifier"


@dataclass
class RulesAndMlPipeline(CategorizationPipeline):
    """Étage 1 : première règle du pack qui matche le libellé.
    Étage 2 : modèle ML si aucune règle ne matche. Modèle absent
    (`modele=None`, ex. fichier gitignoré manquant sur ce poste) → dégradation
    explicite en catégorie par défaut à confiance nulle, pas un plantage
    (doc 08 §5)."""

    regles: tuple[RegleCategorisation, ...]
    modele: ModeleSklearn | None = None

    def categoriser(
        self, dossier_id: DossierId, transaction: NormalizedTransaction
    ) -> ProposedEntry:
        for regle in self.regles:
            if regle.motif.search(transaction.libelle):
                return ProposedEntry(
                    dossier_id=dossier_id,
                    transaction_id=transaction.id,
                    categorie=regle.categorie,
                    etage=Etage.REGLE,
                    confiance=CONFIANCE_PAR_NIVEAU.get(regle.confiance, 0.5),
                )
        return self._via_ml(dossier_id, transaction)

    def _via_ml(self, dossier_id: DossierId, transaction: NormalizedTransaction) -> ProposedEntry:
        if self.modele is None:
            return ProposedEntry(
                dossier_id=dossier_id,
                transaction_id=transaction.id,
                categorie=CATEGORIE_PAR_DEFAUT,
                etage=Etage.ML,
                confiance=0.0,
            )
        categorie, confiance = predire(self.modele, transaction.libelle, transaction.montant_cts)
        return ProposedEntry(
            dossier_id=dossier_id,
            transaction_id=transaction.id,
            categorie=categorie,
            etage=Etage.ML,
            confiance=confiance,
        )
