"""Façade publique de closing/ (doc 03 §3). Squelette : signatures uniquement."""

from __future__ import annotations

from abc import ABC, abstractmethod

from axelcompta.core.ids import DossierId

from .models import LiassePivot


class ClosingService(ABC):
    @abstractmethod
    def cloturer(self, dossier_id: DossierId, exercice: str) -> LiassePivot:
        """Balance → compte de résultat / bilan → LiassePivot (doc 06 §5)."""
