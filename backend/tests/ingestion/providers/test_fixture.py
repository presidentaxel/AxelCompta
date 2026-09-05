from __future__ import annotations

import asyncio
from datetime import date

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.providers.fixture import FixtureProvider, FixtureSettlementProvider

DOSSIER = DossierId("d1")
TENANT = TenantId("t1")
DEPUIS, JUSQUA = date(2026, 8, 1), date(2026, 9, 30)


def test_fixture_provider_rend_la_transaction_du_golden_test_doc17() -> None:
    transactions = asyncio.run(
        FixtureProvider().fetch_transactions(TENANT, DOSSIER, DEPUIS, JUSQUA)
    )
    assert len(transactions) == 1
    assert transactions[0].montant_cts == 848_00
    assert transactions[0].libelle == "UBER BV"


def test_fixture_settlement_provider_rend_le_settlement_du_golden_test_doc17() -> None:
    settlements = asyncio.run(
        FixtureSettlementProvider().fetch_platform_settlements(TENANT, DOSSIER, DEPUIS, JUSQUA)
    )
    assert len(settlements) == 1
    assert settlements[0].gross_earnings_cts == 1_040_00
    assert settlements[0].commission_cts == 192_00
    assert settlements[0].net_payout_cts == 848_00
