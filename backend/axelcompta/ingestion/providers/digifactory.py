"""DigifactoryProvider — transactions bancaires, agrège Bridge par contact (doc 16).

Bloqué à ce jour par un 401 sur le token (doc 16 §7) — implémenté contre des
fixtures qui reproduisent le schéma confirmé (doc 16 §3-4), pas contre un
appel réel. Le jour du déblocage, seule `_recuperer_payload` change (un
appel HTTP au lieu d'un dict figé) ; `parser_transactions` (le parsing, la
partie qui compte) ne bouge pas.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from axelcompta.core.ids import DossierId, TenantId

from .base import DataProvider, NormalizedTransaction, PlatformSettlement, ProviderHealth

# Payload figé au schéma doc 16 §3.1 (objet indexé par accountId) et §4 (champs
# confirmés). Un `deleted` et un `future` sont inclus exprès pour prouver que
# le filtrage (doc 16 §4 : « ne jamais comptabiliser ») fonctionne vraiment.
FIXTURE_PAYLOAD_PAR_DEFAUT: dict[str, list[dict[str, Any]]] = {
    "acc_demo_1": [
        {
            "id": "tx_1",
            "account_id": "acc_demo_1",
            "provider_description": "VIR RECU UBER BV",
            "clean_description": "Uber BV",
            "amount": 848.00,
            "currency_code": "EUR",
            "date": "2026-09-03",
            "updated_at": "2026-09-03T10:00:00",
            "deleted": False,
            "future": False,
            "operation_type": "transfer",
            "category_id": "income",
        },
        {
            "id": "tx_2",
            "account_id": "acc_demo_1",
            "provider_description": "PRELEVEMENT ANNULE",
            "amount": 42.00,
            "currency_code": "EUR",
            "date": "2026-09-04",
            "updated_at": "2026-09-04T08:00:00",
            "deleted": True,
            "future": False,
        },
        {
            "id": "tx_3",
            "account_id": "acc_demo_1",
            "provider_description": "VIREMENT PROGRAMME",
            "amount": 100.00,
            "currency_code": "EUR",
            "date": "2099-01-01",
            "updated_at": "2026-09-04T08:00:00",
            "deleted": False,
            "future": True,
        },
    ]
}


def _vers_centimes(montant: float | str) -> int:
    return int((Decimal(str(montant)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parser_transactions(
    payload: dict[str, list[dict[str, Any]]], dossier_id: DossierId, depuis: date, jusqua: date
) -> list[NormalizedTransaction]:
    """Ne dépend pas de la clé du payload (⚠️ doc 16 §3.1) : la clé indexe la
    réponse mais chaque transaction est prise telle quelle. Filtre
    deleted/future (doc 16 §4) et déduplique par `id`, en gardant
    l'`updated_at` le plus récent (doc 16 §5).
    """
    plus_recentes: dict[str, dict[str, Any]] = {}
    for transactions in payload.values():
        for tx in transactions:
            if tx.get("deleted") or tx.get("future"):
                continue
            existante = plus_recentes.get(tx["id"])
            if existante is None or tx["updated_at"] > existante["updated_at"]:
                plus_recentes[tx["id"]] = tx

    resultat = []
    for tx in plus_recentes.values():
        date_operation = datetime.fromisoformat(tx["date"]).date()
        if depuis <= date_operation <= jusqua:
            resultat.append(
                NormalizedTransaction(
                    dossier_id=dossier_id,
                    date=date_operation,
                    montant_cts=_vers_centimes(tx["amount"]),
                    libelle=str(tx.get("provider_description", "")),
                    source_provider="digifactory",
                    raw_payload=tx,
                )
            )
    return sorted(resultat, key=lambda t: t.date)


class DigifactoryProvider(DataProvider):
    """doc 16. `payload` injectable pour les tests ; par défaut la fixture
    ci-dessus (chemin B, doc 16 §7)."""

    def __init__(self, payload: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._payload = payload if payload is not None else FIXTURE_PAYLOAD_PAR_DEFAUT

    async def fetch_transactions(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[NormalizedTransaction]:
        return parser_transactions(self._payload, dossier_id, since, until)

    async def fetch_platform_settlements(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[PlatformSettlement]:
        return []  # Digifactory ne fournit pas de settlements plateforme (doc 13 §1)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=False, message="token 401 (doc 16 §7) — chemin B (fixtures) actif")
