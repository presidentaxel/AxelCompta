from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, TransactionId
from axelcompta.ingestion.providers.base import NormalizedTransaction, PlatformSettlement
from axelcompta.ingestion.reconciliation import EtatReconciliation, reconcilier

PAYOUT_DATE = date(2026, 9, 2)


def _settlement(net_cts: int = 848_00, payout_date: date = PAYOUT_DATE) -> PlatformSettlement:
    return PlatformSettlement(
        dossier_id=DossierId("d1"),
        platform="uber",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        payout_date=payout_date,
        gross_earnings_cts=1_040_00,
        commission_cts=192_00,
        commission_tva_regime="france_20",
        net_payout_cts=net_cts,
        currency="EUR",
        source_provider="rollee",
        raw_payload={},
    )


def _transaction(
    montant_cts: int, jour: date = date(2026, 9, 3), libelle: str = "VIR UBER BV", id_: str = "tx1"
) -> NormalizedTransaction:
    return NormalizedTransaction(
        id=TransactionId(id_),
        dossier_id=DossierId("d1"),
        date=jour,
        montant_cts=montant_cts,
        libelle=libelle,
        source_provider="digifactory",
        raw_payload={},
    )


def test_reconcilie_sur_montant_exact_dans_la_fenetre_avec_libelle_plateforme() -> None:
    transaction = _transaction(848_00)
    settlement = _settlement()
    (resultat,) = reconcilier((transaction,), (settlement,))
    assert resultat.etat is EtatReconciliation.RECONCILIE
    assert resultat.transaction == transaction


def test_tolere_un_centime_darrondi() -> None:
    (resultat,) = reconcilier((_transaction(848_01),), (_settlement(848_00),))
    assert resultat.etat is EtatReconciliation.RECONCILIE


def test_refuse_un_ecart_de_deux_centimes() -> None:
    (resultat,) = reconcilier((_transaction(848_02),), (_settlement(848_00),))
    assert resultat.etat is EtatReconciliation.EN_ATTENTE_BANQUE


def test_refuse_hors_fenetre_de_date() -> None:
    hors_fenetre = _transaction(848_00, jour=date(2026, 9, 10))  # +8j > +5j
    (resultat,) = reconcilier((hors_fenetre,), (_settlement(),))
    assert resultat.etat is EtatReconciliation.EN_ATTENTE_BANQUE


def test_refuse_si_le_libelle_ne_contient_pas_la_plateforme() -> None:
    autre_libelle = _transaction(848_00, libelle="VIR RECU DIVERS")
    (resultat,) = reconcilier((autre_libelle,), (_settlement(),))
    assert resultat.etat is EtatReconciliation.EN_ATTENTE_BANQUE


def test_aucune_transaction_correspondante_est_en_attente_banque() -> None:
    (resultat,) = reconcilier((_transaction(100_00),), (_settlement(),))
    assert resultat.etat is EtatReconciliation.EN_ATTENTE_BANQUE
    assert resultat.transaction is None


def test_plusieurs_candidats_va_en_revue_manuelle() -> None:
    transactions = (
        _transaction(848_00, id_="tx1"),
        _transaction(848_00, id_="tx2", jour=date(2026, 9, 4)),
    )
    (resultat,) = reconcilier(transactions, (_settlement(),))
    assert resultat.etat is EtatReconciliation.REVUE_MANUELLE
    assert resultat.transaction is None
