"""Implémentation en mémoire de `SignatureRepository` — même rôle que
`decisions_memory.py` : prouve le contrat sans dépendre d'une base, la
suite rapide de tests ne dépend jamais de Postgres pour ça.
"""

from __future__ import annotations

from axelcompta.core.ids import DossierId

from .signature import DocumentSigne, SignatureRepository


class InMemorySignatureRepository(SignatureRepository):
    def __init__(self) -> None:
        self._documents: dict[tuple[DossierId, str], DocumentSigne] = {}

    def enregistrer(
        self, dossier_id: DossierId, type_document: str, document: DocumentSigne
    ) -> None:
        self._documents[(dossier_id, type_document)] = document

    def dernier(self, dossier_id: DossierId, type_document: str) -> DocumentSigne | None:
        return self._documents.get((dossier_id, type_document))
