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
        tel quel (pas de mise à jour silencieuse d'une config comptable).
        Lève `ConfigurationInvalide` (statuts.py) avant toute écriture si la
        configuration fiscale n'a pas de sens."""

    @abstractmethod
    def obtenir(self, dossier_id: DossierId) -> Dossier | None:
        """`None` si le dossier n'existe pas."""

    @abstractmethod
    def lister_par_tenant(self, tenant_id: TenantId) -> tuple[Dossier, ...]:
        """Uniquement les dossiers de ce portefeuille, triés par id."""

    @abstractmethod
    def obtenir_tenant(self, tenant_id: TenantId) -> Tenant | None:
        """`None` si le portefeuille n'existe pas."""

    @abstractmethod
    def lister_tenants(self) -> tuple[Tenant, ...]:
        """Tous les portefeuilles, triés par id (tâches planifiées)."""

    @abstractmethod
    def renommer_tenant(self, tenant_id: TenantId, nom: str) -> None:
        """Le nom affiché du portefeuille, choisi par l'organisation."""

    @abstractmethod
    def ouvrir_exercice(self, dossier: Dossier) -> None:
        """Seule mise à jour de configuration admise : à l'ouverture de
        l'exercice suivant (`axelcompta.exercices`), les bornes et les
        régimes du nouvel exercice. Lève `ConfigurationInvalide` avant
        d'écrire si la nouvelle configuration n'a pas de sens."""

    @abstractmethod
    def retirer(self, dossier_id: DossierId) -> None:
        """Sort le dossier de la liste du portefeuille. Les écritures restent."""

    @abstractmethod
    def par_contact_nr(self, contact_nr: str) -> Dossier | None:
        """Table de correspondance Digifactory `contact_nr -> dossier`
        (doc 16 §9 point 5)."""
