from __future__ import annotations

import asyncio
from datetime import date

import httpx
import pytest

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.providers.digifactory import (
    DigifactoryAuthError,
    DigifactoryHttpClient,
    DigifactoryProvider,
    parser_transactions,
)

DOSSIER = DossierId("d1")
DEPUIS, JUSQUA = date(2026, 1, 1), date(2026, 12, 31)


def test_filtre_deleted_et_future() -> None:
    payload = {
        "acc_1": [
            {
                "id": "tx1",
                "amount": 10.0,
                "date": "2026-06-01",
                "updated_at": "2026-06-01T00:00:00",
                "deleted": False,
                "future": False,
                "provider_description": "OK",
            },
            {
                "id": "tx2",
                "amount": 20.0,
                "date": "2026-06-02",
                "updated_at": "2026-06-02T00:00:00",
                "deleted": True,
                "future": False,
                "provider_description": "SUPPRIME",
            },
            {
                "id": "tx3",
                "amount": 30.0,
                "date": "2099-01-01",
                "updated_at": "2026-06-02T00:00:00",
                "deleted": False,
                "future": True,
                "provider_description": "PROJETE",
            },
        ]
    }
    transactions = parser_transactions(payload, DOSSIER, DEPUIS, JUSQUA)
    assert [t.libelle for t in transactions] == ["OK"]


def test_deduplique_par_id_en_gardant_le_plus_recent() -> None:
    payload = {
        "acc_1": [
            {
                "id": "tx1",
                "amount": 10.0,
                "date": "2026-06-01",
                "updated_at": "2026-06-01T00:00:00",
                "deleted": False,
                "future": False,
                "provider_description": "ancien montant",
            },
            {
                "id": "tx1",
                "amount": 15.0,
                "date": "2026-06-01",
                "updated_at": "2026-06-02T00:00:00",
                "deleted": False,
                "future": False,
                "provider_description": "montant corrigé",
            },
        ]
    }
    transactions = parser_transactions(payload, DOSSIER, DEPUIS, JUSQUA)
    assert len(transactions) == 1
    assert transactions[0].montant_cts == 15_00
    assert transactions[0].libelle == "montant corrigé"


def test_ne_depend_pas_de_la_cle_du_payload() -> None:
    # doc 16 §3.1 : la clé peut ne pas être l'accountId réel, seul le champ
    # account_id sur la transaction (ici absent, tout aussi valide) compte.
    payload = {
        "Bourso": [
            {
                "id": "tx1",
                "amount": 10.0,
                "date": "2026-06-01",
                "updated_at": "2026-06-01T00:00:00",
                "deleted": False,
                "future": False,
                "provider_description": "OK",
            }
        ]
    }
    assert len(parser_transactions(payload, DOSSIER, DEPUIS, JUSQUA)) == 1


def test_provider_utilise_la_fixture_par_defaut() -> None:
    transactions = asyncio.run(
        DigifactoryProvider().fetch_transactions(TenantId("t1"), DOSSIER, DEPUIS, JUSQUA)
    )
    # 1 transaction valide sur les 3 de la fixture (deleted + future exclues)
    assert len(transactions) == 1
    assert transactions[0].montant_cts == 848_00


def test_health_sans_client_reel_signale_les_fixtures() -> None:
    sante = asyncio.run(DigifactoryProvider().health())
    assert sante.ok is False
    assert "fixtures" in sante.message


def test_accepte_le_format_reel_dict_indexe_par_transaction_id() -> None:
    # doc 16 §3.1 documentait une liste par compte ; le payload réel
    # (vérifié 2026-09-11) est un dict {transactionId: transaction} — les
    # valeurs ci-dessous sont fabriquées, pas de vraies données.
    payload = {
        "acc_1": {
            "tx1": {
                "id": "tx1",
                "amount": 10.0,
                "date": "2026-06-01 00:00:00",
                "updated_at": "2026-06-01 00:00:00",
                "deleted": False,
                "future": False,
                "provider_description": "FORMAT REEL",
            }
        }
    }
    transactions = parser_transactions(payload, DOSSIER, DEPUIS, JUSQUA)
    assert [t.libelle for t in transactions] == ["FORMAT REEL"]


def _client_mocke(handler: httpx.MockTransport) -> DigifactoryHttpClient:
    return DigifactoryHttpClient(
        "https://entrepreneur.digifactory.fr/api/bridge",
        "un-token-de-test",
        client=httpx.AsyncClient(
            transport=handler,
            base_url="https://entrepreneur.digifactory.fr/api/bridge",
            headers={"accept": "*/*", "X_DIGI_TOKEN": "un-token-de-test"},
        ),
    )


def test_http_client_envoie_bien_x_digi_token_pas_authorization_bearer() -> None:
    # Non-régression directe de la cause du blocage 2026-09-01/09-11 (doc 16
    # §2, §7) : si un jour quelqu'un « corrige » ça vers Authorization, ce
    # test casse.
    recu: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        recu.update(request.headers)
        return httpx.Response(200, json={})

    client = _client_mocke(httpx.MockTransport(handler))
    asyncio.run(client.categories())
    assert recu.get("x_digi_token") == "un-token-de-test"
    assert "authorization" not in recu


def test_http_client_401_leve_digifactoryautherror() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"exception": "UnauthorizedException", "code": 401}},
        )

    client = _client_mocke(httpx.MockTransport(handler))
    with pytest.raises(DigifactoryAuthError):
        asyncio.run(client.categories())


def test_health_avec_client_reel_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"1": {"id": "1", "name": "Cat"}})

    provider = DigifactoryProvider(client_reel=_client_mocke(httpx.MockTransport(handler)))
    sante = asyncio.run(provider.health())
    assert sante.ok is True


def test_health_avec_client_reel_401() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": 401}})

    provider = DigifactoryProvider(client_reel=_client_mocke(httpx.MockTransport(handler)))
    sante = asyncio.run(provider.health())
    assert sante.ok is False
    assert "401" in sante.message
