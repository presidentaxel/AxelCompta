from __future__ import annotations

from datetime import date

import pytest

from axelcompta.core.ids import DossierId
from axelcompta.ingestion.providers.base import DataProvider, PlatformSettlement


def test_data_provider_est_abstrait() -> None:
    with pytest.raises(TypeError):
        DataProvider()  # type: ignore[abstract]


def test_platform_settlement_porte_le_schema_doc13() -> None:
    settlement = PlatformSettlement(
        dossier_id=DossierId("d1"),
        platform="uber",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        payout_date=date(2026, 9, 2),
        gross_earnings_cts=104_000,
        commission_cts=19_200,
        commission_tva_regime="france_20",
        net_payout_cts=84_800,
        currency="EUR",
        source_provider="rollee",
        raw_payload={},
    )
    assert settlement.net_payout_cts == 84_800
