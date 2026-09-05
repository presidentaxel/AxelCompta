"""Pipeline hybride à étages (doc 05 §1). Squelette : interface uniquement,
aucun étage implémenté.

Démo (doc 17 §3) : seuls les étages règles + ML sont prévus, pas de LLM
d'arbitrage (stub qui passe tout en confiance haute) ni de revue humaine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from axelcompta.core.ids import DossierId
from axelcompta.ingestion.providers.base import NormalizedTransaction

from .models import ProposedEntry


class CategorizationPipeline(ABC):
    @abstractmethod
    def categoriser(
        self,
        dossier_id: DossierId,
        transaction: NormalizedTransaction,
    ) -> ProposedEntry:
        """Fait traverser les étages (doc 05 §1) jusqu'à obtenir une proposition."""
