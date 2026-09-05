"""Teste la composition root de la démo (doc 17 semaine 0) — la couture
complète, pas les briques individuelles (déjà testées module par module :
fixtures en tests/ingestion/providers/, réconciliation en
tests/ingestion/test_reconciliation.py, invariant d'équilibre en
tests/ledger/test_invariants.py).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from axelcompta.core.ids import DossierId
from axelcompta.demo import construire_ecriture_bouchon, executer
from axelcompta.ingestion.providers.base import NormalizedTransaction, PlatformSettlement
from axelcompta.ledger.invariants import solde


def test_executer_produit_un_pdf_valide(tmp_path: Path) -> None:
    destination = tmp_path / "liasse.pdf"
    resultat = executer(destination)
    assert resultat == destination
    assert destination.read_bytes().startswith(b"%PDF-")


def test_construire_ecriture_bouchon_reproduit_le_golden_test_doc17_paragraphe_7() -> None:
    # Settlement Uber 1 040,00 € TTC / commission 192,00 € TTC / net 848,00 €,
    # réconcilié avec la transaction bancaire +848,00 € UBER BV (doc 17 §7).
    # Sans ventilation TVA à ce stade (semaine 0, doc 13 §5.3 pour semaine 2) :
    # juste 512 débit / 706 crédit à 848,00 €, équilibrée.
    transaction = NormalizedTransaction(
        dossier_id=DossierId("demo-1"),
        date=date(2026, 9, 3),
        montant_cts=848_00,
        libelle="UBER BV",
        source_provider="fixture",
        raw_payload={},
    )
    settlement = PlatformSettlement(
        dossier_id=DossierId("demo-1"),
        platform="uber",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        payout_date=date(2026, 9, 2),
        gross_earnings_cts=1_040_00,
        commission_cts=192_00,
        commission_tva_regime="france_20",
        net_payout_cts=848_00,
        currency="EUR",
        source_provider="fixture",
        raw_payload={},
    )
    ecriture = construire_ecriture_bouchon(transaction, settlement, numero=1)
    debit, credit = solde(ecriture)
    assert debit == credit
    assert debit.centimes == 848_00
