"""Frontière de persistance des dossiers (doc 03 §3bis). Toute lecture
d'un dossier pour le compte d'un gestionnaire passe par `tenant_id` : c'est
ici, et pas dans chaque route, que l'isolation entre portefeuilles se joue.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from axelcompta.core.ids import DossierId, TenantId

from .models import Dossier, Tenant


class DossierRepository(ABC):
    @abstractmethod
    def enregistrer_tenant(self, tenant: Tenant) -> None:
        """Idempotent : un tenant déjà présent est laissé tel quel."""

    @abstractmethod
    def enregistrer(self, dossier: Dossier) -> None:
        """Idempotent sur `dossier.id` : un dossier déjà présent est laissé
        tel quel (pas de mise à jour silencieuse d'une config comptable)."""

    @abstractmethod
    def obtenir(self, dossier_id: DossierId) -> Dossier | None:
        """`None` si le dossier n'existe pas."""

    @abstractmethod
    def lister_par_tenant(self, tenant_id: TenantId) -> tuple[Dossier, ...]:
        """Uniquement les dossiers de ce portefeuille, triés par id."""

    @abstractmethod
    def par_contact_nr(self, contact_nr: str) -> Dossier | None:
        """Table de correspondance Digifactory `contact_nr -> dossier`
        (doc 16 §9 point 5)."""
