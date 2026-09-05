"""FilingRenderer — un renderer par format de sortie, tous branchés sur le
même LiassePivot (doc 02 §5, doc 06 §6). Squelette : interface uniquement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from axelcompta.closing.models import LiassePivot


class FilingRenderer(ABC):
    @abstractmethod
    def rendre(self, liasse: LiassePivot) -> bytes:
        """Démo (doc 17 semaine 3) : PDF simplifié, pas de conformité CERFA/DGFiP
        stricte. V1 : FEC, EDI-TDFC, dossier INPI (doc 02)."""
