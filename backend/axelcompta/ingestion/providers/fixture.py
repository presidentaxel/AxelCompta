"""FixtureProvider / FixtureSettlementProvider — bouchons pour le squelette
bout-en-bout de la démo (doc 17, chemin B / semaine 0).

Squelette d'interfaces uniquement : pas encore de données bidons générées.
"""

from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.providers.base import (
    DataProvider,
    NormalizedTransaction,
    PlatformSettlement,
    ProviderHealth,
)


class FixtureProvider(DataProvider):
    """Transactions bancaires bidons (doc 17 semaine 0) — chemin B côté banque."""

    async def fetch_transactions(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[NormalizedTransaction]:
        raise NotImplementedError("doc 17 semaine 0")

    async def fetch_platform_settlements(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[PlatformSettlement]:
        return []

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, message="fixture : toujours disponible")


class FixtureSettlementProvider(DataProvider):
    """Settlements Rollee bidons, calés main sur les transactions bancaires
    choisies pour la démo (doc 17 §5 chemin B, doc 13 §4.1)."""

    async def fetch_transactions(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[NormalizedTransaction]:
        return []

    async def fetch_platform_settlements(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[PlatformSettlement]:
        raise NotImplementedError("doc 17 semaine 0")

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, message="fixture : toujours disponible")
