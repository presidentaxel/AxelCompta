"""Implémentation en mémoire de LedgerService — pour la démo semaine 0 (doc 17) :
prouve la couture réconciliation → écriture → clôture sans dépendre de
Postgres. `repository.py` fournit l'implémentation Postgres réelle.
"""

from __future__ import annotations

from axelcompta.core.ids import DossierId, EcritureId

from .invariants import verifier_equilibre
from .models import Ecriture
from .service import LedgerService


class InMemoryLedgerService(LedgerService):
    def __init__(self) -> None:
        self._par_dossier: dict[DossierId, list[Ecriture]] = {}

    def enregistrer(self, ecriture: Ecriture) -> EcritureId:
        verifier_equilibre(ecriture)
        self._par_dossier.setdefault(ecriture.dossier_id, []).append(ecriture)
        return ecriture.id

    def grand_livre(self, dossier_id: DossierId) -> tuple[Ecriture, ...]:
        return tuple(sorted(self._par_dossier.get(dossier_id, []), key=lambda e: e.date))
