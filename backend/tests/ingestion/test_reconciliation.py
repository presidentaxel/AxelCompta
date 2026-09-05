from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId
from axelcompta.ingestion.providers.base import NormalizedTransaction, PlatformSettlement
from axelcompta.ingestion.reconciliation import reconcilier_bouchon


def _settlement(net_cts: int) -> PlatformSettlement:
    return PlatformSettlement(
        dossier_id=DossierId("d1"),
        platform="uber",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        payout_date=date(2026, 9, 2),
        gross_earnings_cts=1_040_00,
        commission_cts=192_00,
        commission_tva_regime="france_20",
        net_payout_cts=net_cts,
        currency="EUR",
        source_provider="rollee",
        raw_payload={},
    )


def _transaction(montant_cts: int) -> NormalizedTransaction:
    return NormalizedTransaction(
        dossier_id=DossierId("d1"),
        date=date(2026, 9, 3),
        montant_cts=montant_cts,
        libelle="UBER BV",
        source_provider="digifactory",
        raw_payload={},
    )


def test_appaire_sur_montant_exact_unique() -> None:
    transactions = (_transaction(848_00),)
    settlements = (_settlement(848_00),)
    paires = reconcilier_bouchon(transactions, settlements)
    assert paires == ((transactions[0], settlements[0]),)


def test_ignore_un_settlement_sans_transaction_correspondante() -> None:
    assert reconcilier_bouchon((_transaction(100_00),), (_settlement(848_00),)) == ()


def test_ignore_un_settlement_avec_plusieurs_candidats() -> None:
    transactions = (_transaction(848_00), _transaction(848_00))
    assert reconcilier_bouchon(transactions, (_settlement(848_00),)) == ()
