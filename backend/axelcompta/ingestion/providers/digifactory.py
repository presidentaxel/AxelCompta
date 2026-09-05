"""DigifactoryProvider — transactions bancaires, agrège Bridge par contact (doc 16).

Bloqué à ce jour par un 401 sur le token (doc 16 §7) — squelette uniquement,
aucun appel réseau implémenté.
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


class DigifactoryProvider(DataProvider):
    """Voir doc 16 pour le détail de l'intégration (auth, endpoints, filtrage)."""

    async def fetch_transactions(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[NormalizedTransaction]:
        raise NotImplementedError("doc 17 semaine 1 — chemin A, bloqué par le 401 (doc 16 §7)")

    async def fetch_platform_settlements(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[PlatformSettlement]:
        return []  # Digifactory ne fournit pas de settlements plateforme (doc 13 §1)

    async def health(self) -> ProviderHealth:
        raise NotImplementedError("doc 17 semaine 1")
