"""Implémentation en mémoire de DossierRepository, pour les tests rapides
(même rôle que `ledger/memory.py` : prouve le contrat sans base)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from axelcompta.core.ids import DossierId, TenantId

from .models import Dossier, Tenant
from .repository import DossierRepository
from .statuts import configuration_de


class InMemoryDossierRepository(DossierRepository):
    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._dossiers: dict[str, Dossier] = {}

    def enregistrer_tenant(self, tenant: Tenant) -> None:
        self._tenants.setdefault(tenant.id, tenant)

    def enregistrer(self, dossier: Dossier) -> None:
        if dossier.tenant_id not in self._tenants:
            raise ValueError(f"tenant inconnu : {dossier.tenant_id}")
        configuration_de(dossier)
        self._dossiers.setdefault(dossier.id, dossier)

    def obtenir(self, dossier_id: DossierId) -> Dossier | None:
        return self._dossiers.get(dossier_id)

    def lister_par_tenant(self, tenant_id: TenantId) -> tuple[Dossier, ...]:
        return tuple(
            sorted(
                (
                    d
                    for d in self._dossiers.values()
                    if d.tenant_id == tenant_id and d.retire_le is None
                ),
                key=lambda d: d.id,
            )
        )

    def obtenir_tenant(self, tenant_id: TenantId) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def lister_tenants(self) -> tuple[Tenant, ...]:
        return tuple(sorted(self._tenants.values(), key=lambda t: t.id))

    def renommer_tenant(self, tenant_id: TenantId, nom: str) -> None:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise ValueError(f"tenant inconnu : {tenant_id}")
        self._tenants[tenant_id] = Tenant(id=tenant.id, nom=nom)

    def retirer(self, dossier_id: DossierId) -> None:
        dossier = self._dossiers.get(dossier_id)
        if dossier is None:
            raise ValueError(f"dossier inconnu : {dossier_id}")
        self._dossiers[dossier_id] = replace(dossier, retire_le=date.today())

    def par_contact_nr(self, contact_nr: str) -> Dossier | None:
        return next((d for d in self._dossiers.values() if d.contact_nr == contact_nr), None)
