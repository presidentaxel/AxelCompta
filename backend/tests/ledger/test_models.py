from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens


def test_ecriture_porte_ses_lignes() -> None:
    ecriture = Ecriture(
        id=EcritureId("e1"),
        dossier_id=DossierId("d1"),
        journal=Journal.BQ,
        date=date(2026, 9, 1),
        libelle="Virement Uber",
        reference_piece=None,
        lignes=(
            LigneEcriture(compte="512", sens=Sens.DEBIT, montant=Money(84_800)),
            LigneEcriture(compte="706", sens=Sens.CREDIT, montant=Money(84_800)),
        ),
    )
    assert len(ecriture.lignes) == 2
    assert ecriture.journal is Journal.BQ


def test_les_5_journaux_v1_existent() -> None:
    assert {j.name for j in Journal} == {"BQ", "AC", "VE", "OD", "AN"}
