from __future__ import annotations

from datetime import date

from axelcompta.closing.bouchon import BouchonClosingService
from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

DOSSIER = DossierId("d1")


def test_cloture_bouchon_calcule_le_solde_par_compte() -> None:
    ledger = InMemoryLedgerService()
    ledger.enregistrer(
        Ecriture(
            id=EcritureId("e1"),
            dossier_id=DOSSIER,
            journal=Journal.BQ,
            date=date(2026, 9, 3),
            libelle="test",
            reference_piece=None,
            lignes=(
                LigneEcriture(compte="512", sens=Sens.DEBIT, montant=Money(848_00)),
                LigneEcriture(compte="706", sens=Sens.CREDIT, montant=Money(848_00)),
            ),
        )
    )
    liasse = BouchonClosingService(ledger).cloturer(DOSSIER, exercice="2026")
    assert liasse.cases == {"512": 848_00, "706": -848_00}


def test_cloture_bouchon_sur_dossier_vide() -> None:
    liasse = BouchonClosingService(InMemoryLedgerService()).cloturer(DOSSIER, exercice="2026")
    assert liasse.cases == {}
