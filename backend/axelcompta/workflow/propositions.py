"""Propositions d'origine du pipeline, conservées par écriture (doc 05 §5,
doc 07 §3.1). Voir le commentaire de `orm.propositions_categorisation`."""

from __future__ import annotations

from abc import ABC, abstractmethod

from axelcompta.categorize.models import ProposedEntry
from axelcompta.core.ids import DossierId, EcritureId


class PropositionRepository(ABC):
    @abstractmethod
    def enregistrer(self, ecriture_id: EcritureId, proposition: ProposedEntry) -> None:
        """Idempotent : la proposition d'origine d'une écriture déjà connue
        n'est pas remplacée."""

    @abstractmethod
    def obtenir(self, dossier_id: DossierId, ecriture_id: EcritureId) -> ProposedEntry | None:
        """`None` si l'écriture n'a pas de proposition (ex. écriture de
        settlement, construite sans passer par le pipeline)."""


class InMemoryPropositionRepository(PropositionRepository):
    def __init__(self) -> None:
        self._propositions: dict[EcritureId, ProposedEntry] = {}

    def enregistrer(self, ecriture_id: EcritureId, proposition: ProposedEntry) -> None:
        self._propositions.setdefault(ecriture_id, proposition)

    def obtenir(self, dossier_id: DossierId, ecriture_id: EcritureId) -> ProposedEntry | None:
        proposition = self._propositions.get(ecriture_id)
        if proposition is None or proposition.dossier_id != dossier_id:
            return None
        return proposition
