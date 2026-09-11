"""Implémentation en mémoire de `SignatureRepository` — même rôle que
`decisions_memory.py` : prouve le contrat sans dépendre d'une base, la
suite rapide de tests ne dépend jamais de Postgres pour ça. Append-only
(doc 18, doc 20 §4bis) — même structure que `InMemoryDecisionRepository`.
"""

from __future__ import annotations

from axelcompta.core.ids import DossierId

from .signature import DocumentSigne, SignatureRepository


class InMemorySignatureRepository(SignatureRepository):
    def __init__(self) -> None:
        self._documents: dict[tuple[DossierId, str], list[DocumentSigne]] = {}

    def enregistrer(
        self, dossier_id: DossierId, type_document: str, document: DocumentSigne
    ) -> None:
        self._documents.setdefault((dossier_id, type_document), []).append(document)

    def dernier(self, dossier_id: DossierId, type_document: str) -> DocumentSigne | None:
        historique = self._documents.get((dossier_id, type_document), [])
        return max(historique, key=lambda d: d.signe_le) if historique else None

    def lister(self, dossier_id: DossierId, type_document: str) -> tuple[DocumentSigne, ...]:
        historique = self._documents.get((dossier_id, type_document), [])
        return tuple(sorted(historique, key=lambda d: d.signe_le))
