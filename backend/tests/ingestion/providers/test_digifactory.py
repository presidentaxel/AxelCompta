from __future__ import annotations

import asyncio
from datetime import date

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.providers.digifactory import DigifactoryProvider, parser_transactions

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


def test_health_signale_le_blocage_401() -> None:
    sante = asyncio.run(DigifactoryProvider().health())
    assert sante.ok is False
    assert "401" in sante.message
