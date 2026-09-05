"""RolleeProvider — settlements plateformes gig, mode fleet B2B (doc 13 §3).

Accès sandbox non encore vérifié à ce jour (doc 17 §5) — implémenté contre
des fixtures `PlatformSettlement` construites à la main (doc 17 §5 chemin B),
calées sur les mêmes transactions bancaires que le golden test (doc 17 §7) :
même montant net (848,00 €), même fenêtre de date. Le jour où l'accès
sandbox est confirmé, `_recuperer_settlements` devient un appel HTTP réel ;
rien d'autre ne bouge.
"""

from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, TenantId

from .base import DataProvider, NormalizedTransaction, PlatformSettlement, ProviderHealth


def _fixture_par_defaut(dossier_id: DossierId) -> tuple[PlatformSettlement, ...]:
    return (
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
            source_provider="rollee",
            raw_payload={},
        ),
    )


class RolleeProvider(DataProvider):
    """doc 13 §3. `settlements` injectable pour les tests ; par défaut la
    fixture calée sur le golden test doc 17 §7 (chemin B, doc 17 §5)."""

    def __init__(self, settlements: tuple[PlatformSettlement, ...] | None = None) -> None:
        self._settlements = settlements

    async def fetch_transactions(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[NormalizedTransaction]:
        return []  # Rollee ne fournit pas de transactions bancaires (doc 13 §1)

    async def fetch_platform_settlements(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[PlatformSettlement]:
        settlements = self._settlements or _fixture_par_defaut(dossier_id)
        return [s for s in settlements if since <= s.payout_date <= until]

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            ok=False, message="accès sandbox non vérifié (doc 17 §5) — chemin B (fixtures) actif"
        )
