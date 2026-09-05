"""FixtureProvider / FixtureSettlementProvider — bouchons pour le squelette
bout-en-bout de la démo (doc 17, chemin B / semaine 0).

Les données sont le golden test du doc 17 §7 : settlement Uber
1 040,00 € TTC / commission 192,00 € TTC / net 848,00 €, réconcilié avec la
transaction bancaire +848,00 € UBER BV. Servent à valider la couture
réconciliation → écriture → clôture avant d'investir dans la justesse des
vrais providers (semaine 1).
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
        return [
            NormalizedTransaction(
                dossier_id=dossier_id,
                date=date(2026, 9, 3),
                montant_cts=848_00,
                libelle="UBER BV",
                source_provider="fixture",
                raw_payload={},
            )
        ]

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
        return [
            PlatformSettlement(
                dossier_id=dossier_id,
                platform="uber",
                period_start=date(2026, 8, 1),
                period_end=date(2026, 8, 31),
                payout_date=date(2026, 9, 2),
                gross_earnings_cts=1_040_00,
                commission_cts=192_00,
                commission_tva_regime="france_20",
                net_payout_cts=848_00,
                currency="EUR",
                source_provider="fixture",
                raw_payload={},
            )
        ]

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, message="fixture : toujours disponible")
