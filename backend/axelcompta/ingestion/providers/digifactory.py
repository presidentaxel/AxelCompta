"""DigifactoryProvider — transactions bancaires, agrège Bridge par contact (doc 16).

**Débloqué le 2026-09-11** (doc 16 §7) : le 401 venait d'un mauvais type
d'en-tête documenté depuis le début (`Authorization: Bearer`), pas d'un
problème Digifactory ou client. Le bon en-tête est `X_DIGI_TOKEN` (shared
secret). Vérifié par appel réel sur `/contacts`, `/categories`,
`/accounts/{nr}` et `/transactions/{nr}` — voir `DigifactoryHttpClient`
ci-dessous pour le chemin A (vrais appels HTTP).

`DigifactoryProvider` (chemin `DataProvider`, en bas de fichier) reste sur
fixtures par défaut : brancher `client_reel` (`DigifactoryHttpClient`) fait
passer `health()` en vrai appel, mais `fetch_transactions`/
`fetch_platform_settlements` ne peuvent pas encore appeler l'API réelle
pour un `dossier_id` donné — il manque la table de correspondance
`contact_nr → dossier_id` (doc 16 §9 point 5, jamais construite, ~200
chauffeurs). Pas fait ici : inventer ce mapping avant d'avoir la vraie
liste serait fabriqué, pas réel.

`parser_transactions` a un vrai écart trouvé en testant contre de vraies
données (2026-09-11) : le payload réel indexe chaque compte par un **dict
`{transactionId: transaction}`**, pas une liste comme documenté au départ
(doc 16 §3.1) — `_transactions_de_compte` normalise les deux formes.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

import httpx

from axelcompta.core.ids import DossierId, TenantId, TransactionId

from .base import DataProvider, NormalizedTransaction, PlatformSettlement, ProviderHealth

# Payload JSON brut du fournisseur — forme non figée à dessein (`Any` au
# niveau compte) : un compte peut être une liste de transactions (doc 16
# §3.1 documenté) ou un dict {transactionId: transaction} (réel, vérifié
# 2026-09-11, voir `_transactions_de_compte`) ; `Mapping` plutôt que `dict`
# pour rester covariant (les littéraux de test n'ont pas besoin de coller
# exactement au type).
PayloadTransactions = Mapping[str, Any]

# Payload figé au schéma doc 16 §3.1 (objet indexé par accountId) et §4 (champs
# confirmés). Un `deleted` et un `future` sont inclus exprès pour prouver que
# le filtrage (doc 16 §4 : « ne jamais comptabiliser ») fonctionne vraiment.
FIXTURE_PAYLOAD_PAR_DEFAUT: PayloadTransactions = {
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


def _transactions_de_compte(valeur: Any) -> list[dict[str, Any]]:
    """Chaque compte du payload `/transactions` est documenté (doc 16 §3.1)
    comme une **liste** de transactions. **Réel, vérifié le 2026-09-11** :
    c'est en fait un **dict `{transactionId: transaction}`**. Accepte les
    deux formes plutôt que de figer sur l'une — la fixture de test garde
    le format liste (plus simple à lire), le payload réel capturé est un
    dict ; aucune raison de réécrire les fixtures existantes pour ça."""
    if isinstance(valeur, dict):
        return cast("list[dict[str, Any]]", list(valeur.values()))
    return cast("list[dict[str, Any]]", valeur)


def parser_transactions(
    payload: PayloadTransactions,
    dossier_id: DossierId,
    depuis: date,
    jusqua: date,
) -> list[NormalizedTransaction]:
    """Ne dépend pas de la clé du payload (⚠️ doc 16 §3.1) : la clé indexe la
    réponse mais chaque transaction est prise telle quelle. Filtre
    deleted/future (doc 16 §4) et déduplique par `id`, en gardant
    l'`updated_at` le plus récent (doc 16 §5).
    """
    plus_recentes: dict[str, dict[str, Any]] = {}
    for compte in payload.values():
        for tx in _transactions_de_compte(compte):
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
                    id=TransactionId(str(tx["id"])),
                    dossier_id=dossier_id,
                    date=date_operation,
                    montant_cts=_vers_centimes(tx["amount"]),
                    libelle=str(tx.get("provider_description", "")),
                    source_provider="digifactory",
                    raw_payload=tx,
                )
            )
    return sorted(resultat, key=lambda t: t.date)


FORMAT_DATE_DIGIFACTORY = "%Y-%m-%d %H:%M:%S"  # doc 16 §1, sans fuseau (⚠️ à confirmer)


class DigifactoryAuthError(RuntimeError):
    """401 réel de l'API — distinct d'une erreur réseau (doc 16 §1 : le
    token est révocable à tout moment, ce cas doit être géré explicitement)."""


class DigifactoryHttpClient:
    """Chemin A (doc 16 §7) : vrais appels HTTP à l'API Digifactory.

    Auth confirmée en réel le 2026-09-11 : en-tête `X_DIGI_TOKEN: <token>`
    — **pas** `Authorization: Bearer` (doc 16 §2, deux types de token chez
    Digifactory, la spec initiale nous avait donné l'autre). `/contacts`,
    `/categories`, `/accounts/{nr}` et `/transactions/{nr}` tous vérifiés
    200 en réel avec cet en-tête.

    N'appelle jamais l'API à la construction (même règle que
    `SupabaseCompteRepository`, doc 17 §9 bloc B) — seulement à la première
    méthode effectivement invoquée.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client_fourni = client is not None
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={"accept": "*/*", "X_DIGI_TOKEN": token},
            timeout=timeout,
        )

    @classmethod
    def depuis_env(cls) -> DigifactoryHttpClient:
        """Lit `DIGIFACTORY_BASE_URL`/`DIGIFACTORY_TOKEN` (`.env`, doc 16 §2)."""
        base_url = os.environ.get("DIGIFACTORY_BASE_URL")
        token = os.environ.get("DIGIFACTORY_TOKEN")
        if not base_url or not token:
            raise RuntimeError(
                "DIGIFACTORY_BASE_URL/DIGIFACTORY_TOKEN manquantes — "
                "voir .env.example à la racine du repo"
            )
        return cls(base_url, token)

    async def _get(self, chemin: str, params: dict[str, str] | None = None) -> Any:
        reponse = await self._client.get(chemin, params=params)
        if reponse.status_code == 401:
            raise DigifactoryAuthError(f"401 sur {chemin} — token invalide/révoqué (doc 16 §1)")
        reponse.raise_for_status()
        return reponse.json()

    async def contacts(self) -> dict[str, Any]:
        """doc 16 §3.3 : objet indexé par `nr`."""
        return cast(dict[str, Any], await self._get("/contacts"))

    async def accounts(self, contact_nr: str | int) -> dict[str, Any] | list[Any]:
        """doc 16 §3.2. **Réel (2026-09-11)** : `[]` (liste vide, pas `{}`)
        quand le contact n'a aucun compte connecté."""
        return cast("dict[str, Any] | list[Any]", await self._get(f"/accounts/{contact_nr}"))

    async def transactions(
        self, contact_nr: str | int, since: datetime | None = None
    ) -> PayloadTransactions:
        """doc 16 §3.1. `since` est le mode nominal (filtre `updated_at`) —
        sans lui, **le premier appel peut être volumineux** (doc 16 §5,
        confirmé en réel : ~800 Ko/2000 transactions pour un seul contact
        sans filtre)."""
        params = {"since": since.strftime(FORMAT_DATE_DIGIFACTORY)} if since else None
        return cast(
            PayloadTransactions, await self._get(f"/transactions/{contact_nr}", params=params)
        )

    async def categories(self) -> dict[str, Any]:
        return cast(dict[str, Any], await self._get("/categories"))

    async def aclose(self) -> None:
        if not self._client_fourni:
            await self._client.aclose()


class DigifactoryProvider(DataProvider):
    """doc 16. `payload` injectable pour les tests ; par défaut la fixture
    ci-dessus (chemin B, doc 16 §7).

    `client_reel` (optionnel) : un `DigifactoryHttpClient` pour que
    `health()` fasse un vrai appel plutôt que de retourner le message figé
    "fixtures actives". **`fetch_transactions`/`fetch_platform_settlements`
    n'utilisent pas encore `client_reel`** — il manque la table de
    correspondance `contact_nr → dossier_id` (doc 16 §9 point 5, jamais
    construite) pour savoir quel contact Digifactory appeler pour un
    `dossier_id` donné. Le brancher pour de vrai est la suite logique une
    fois cette table réelle disponible, pas avant."""

    def __init__(
        self,
        payload: PayloadTransactions | None = None,
        client_reel: DigifactoryHttpClient | None = None,
    ) -> None:
        self._payload = payload if payload is not None else FIXTURE_PAYLOAD_PAR_DEFAUT
        self._client_reel = client_reel

    async def fetch_transactions(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[NormalizedTransaction]:
        return parser_transactions(self._payload, dossier_id, since, until)

    async def fetch_platform_settlements(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[PlatformSettlement]:
        return []  # Digifactory ne fournit pas de settlements plateforme (doc 13 §1)

    async def health(self) -> ProviderHealth:
        if self._client_reel is None:
            return ProviderHealth(
                ok=False, message="chemin B (fixtures) actif — aucun DigifactoryHttpClient fourni"
            )
        try:
            await self._client_reel.categories()
        except DigifactoryAuthError as erreur:
            return ProviderHealth(ok=False, message=str(erreur))
        except httpx.HTTPError as erreur:
            return ProviderHealth(ok=False, message=f"erreur réseau/HTTP : {erreur}")
        return ProviderHealth(
            ok=True, message="X_DIGI_TOKEN valide (doc 16 §7, débloqué 2026-09-11)"
        )
