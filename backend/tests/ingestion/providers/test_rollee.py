from __future__ import annotations

import asyncio
from datetime import date

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.providers.base import PlatformSettlement
from axelcompta.ingestion.providers.rollee import RolleeProvider

DOSSIER = DossierId("d1")


def test_fixture_par_defaut_reproduit_le_golden_test_doc17() -> None:
    settlements = asyncio.run(
        RolleeProvider().fetch_platform_settlements(
            TenantId("t1"), DOSSIER, date(2026, 1, 1), date(2026, 12, 31)
        )
    )
    assert len(settlements) == 1
    assert settlements[0].net_payout_cts == 848_00
    assert settlements[0].platform == "uber"


def test_filtre_par_fenetre_de_payout_date() -> None:
    settlements = asyncio.run(
        RolleeProvider().fetch_platform_settlements(
            TenantId("t1"), DOSSIER, date(2020, 1, 1), date(2020, 12, 31)
        )
    )
    assert settlements == []


def test_settlements_injectes_remplacent_la_fixture() -> None:
    injecte = PlatformSettlement(
        dossier_id=DOSSIER,
        platform="bolt",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        payout_date=date(2026, 2, 1),
        gross_earnings_cts=500_00,
        commission_cts=50_00,
        commission_tva_regime="autoliquidation_ue",
        net_payout_cts=450_00,
        currency="EUR",
        source_provider="rollee",
        raw_payload={},
    )
    settlements = asyncio.run(
        RolleeProvider(settlements=(injecte,)).fetch_platform_settlements(
            TenantId("t1"), DOSSIER, date(2026, 1, 1), date(2026, 12, 31)
        )
    )
    assert settlements == [injecte]


def test_health_signale_lacces_sandbox_non_verifie() -> None:
    sante = asyncio.run(RolleeProvider().health())
    assert sante.ok is False
