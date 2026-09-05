from __future__ import annotations

from datetime import date

import pytest

from axelcompta.core.errors import InvariantViole
from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.invariants import solde, verifier_equilibre
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens


def _ecriture(lignes: tuple[LigneEcriture, ...]) -> Ecriture:
    return Ecriture(
        id=EcritureId("e1"),
        dossier_id=DossierId("d1"),
        journal=Journal.BQ,
        date=date(2026, 9, 1),
        libelle="test",
        reference_piece=None,
        lignes=lignes,
    )


def test_solde_equilibre_ne_leve_rien() -> None:
    ecriture = _ecriture(
        (
            LigneEcriture(compte="512", sens=Sens.DEBIT, montant=Money(848_00)),
            LigneEcriture(compte="706", sens=Sens.CREDIT, montant=Money(848_00)),
        )
    )
    debit, credit = solde(ecriture)
    assert debit == credit == Money(848_00)
    verifier_equilibre(ecriture)  # ne lève pas


def test_ecriture_desequilibree_leve_invariant_viole() -> None:
    ecriture = _ecriture(
        (
            LigneEcriture(compte="512", sens=Sens.DEBIT, montant=Money(848_00)),
            LigneEcriture(compte="706", sens=Sens.CREDIT, montant=Money(1_00)),
        )
    )
    with pytest.raises(InvariantViole):
        verifier_equilibre(ecriture)


def test_ecriture_sans_ligne_leve_invariant_viole() -> None:
    with pytest.raises(InvariantViole):
        verifier_equilibre(_ecriture(()))
