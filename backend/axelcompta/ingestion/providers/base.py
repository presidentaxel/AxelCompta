"""ABC DataProvider + types partagés (doc 13 §2.2).

Contrat unique pour toute source de données d'entrée — la config du dossier
détermine quel(s) provider(s) sont actifs, jamais de branchement conditionnel
dans le code métier. Squelette : signatures uniquement, aucune implémentation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from axelcompta.core.ids import DossierId, TenantId


@dataclass(frozen=True, slots=True)
class NormalizedTransaction:
    """Transaction bancaire normalisée (doc 04 §5 : la sortie unique du module)."""

    dossier_id: DossierId
    date: date
    montant_cts: int
    libelle: str
    source_provider: str
    raw_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class PlatformSettlement:
    """Relevé de plateforme gig — Uber, Bolt... (doc 13 §4.1)."""

    dossier_id: DossierId
    platform: str
    period_start: date
    period_end: date
    payout_date: date
    gross_earnings_cts: int
    commission_cts: int
    commission_tva_regime: str
    net_payout_cts: int
    currency: str
    source_provider: str
    raw_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """Santé de la connexion (consentement valide, quota restant...)."""

    ok: bool
    message: str


class DataProvider(ABC):
    """Contrat unique pour toute source de données d'entrée (doc 13 §2.2)."""

    @abstractmethod
    async def fetch_transactions(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[NormalizedTransaction]:
        """Transactions bancaires normalisées."""

    @abstractmethod
    async def fetch_platform_settlements(
        self,
        tenant_id: TenantId,
        dossier_id: DossierId,
        since: date,
        until: date,
    ) -> list[PlatformSettlement]:
        """Relevés de plateformes (Uber, Bolt...). Peut retourner [] si non supporté."""

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Santé de la connexion (consentement valide, quota restant...)."""
