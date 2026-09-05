"""FileImportProvider — CSV/XLSX/ODS/OFX/QIF (doc 04 §3).

Sert aussi de chemin C (filet) pour la démo : rejoue
`_AUDIT_DONNEES/resultats/fec_ml_taxonomie.csv` (doc 17 §4).
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


class FileImportProvider(DataProvider):
    """Voir doc 04 §3 pour les profils d'import supportés."""

    async def fetch_transactions(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[NormalizedTransaction]:
        raise NotImplementedError("doc 17 semaine 1 — chemin C (filet), rejoue le CSV audit")

    async def fetch_platform_settlements(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[PlatformSettlement]:
        return []  # les fichiers importés ne portent pas de settlements plateforme

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, message="import fichier : pas de connexion externe")
