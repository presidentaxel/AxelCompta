"""RolleeProvider — settlements plateformes gig, mode fleet B2B (doc 13 §3).

Accès sandbox non encore vérifié à ce jour (doc 17 §5) — squelette uniquement.
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


class RolleeProvider(DataProvider):
    """Voir doc 13 §3 pour le détail (endpoints, webhooks, polling de secours)."""

    async def fetch_transactions(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[NormalizedTransaction]:
        return []  # Rollee ne fournit pas de transactions bancaires (doc 13 §1)

    async def fetch_platform_settlements(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[PlatformSettlement]:
        raise NotImplementedError("doc 17 §5 — vérifier l'accès sandbox en premier")

    async def health(self) -> ProviderHealth:
        raise NotImplementedError("doc 17 §5")
