from __future__ import annotations

from datetime import date

import pytest

from axelcompta.core.errors import InvariantViole
from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens


def _ecriture_equilibree(id_: str, jour: int) -> Ecriture:
    return Ecriture(
        id=EcritureId(id_),
        dossier_id=DossierId("d1"),
        journal=Journal.BQ,
        date=date(2026, 9, jour),
        libelle="test",
        reference_piece=None,
        lignes=(
            LigneEcriture(compte="512", sens=Sens.DEBIT, montant=Money(100_00)),
            LigneEcriture(compte="706", sens=Sens.CREDIT, montant=Money(100_00)),
        ),
    )


def test_enregistrer_puis_relire_le_grand_livre_trie_par_date() -> None:
    service = InMemoryLedgerService()
    service.enregistrer(_ecriture_equilibree("e2", jour=5))
    service.enregistrer(_ecriture_equilibree("e1", jour=1))
    grand_livre = service.grand_livre(DossierId("d1"))
    assert [e.id for e in grand_livre] == ["e1", "e2"]


def test_enregistrer_une_ecriture_desequilibree_leve_et_ne_persiste_pas() -> None:
    service = InMemoryLedgerService()
    ecriture = Ecriture(
        id=EcritureId("e1"),
        dossier_id=DossierId("d1"),
        journal=Journal.BQ,
        date=date(2026, 9, 1),
        libelle="test",
        reference_piece=None,
        lignes=(LigneEcriture(compte="512", sens=Sens.DEBIT, montant=Money(100_00)),),
    )
    with pytest.raises(InvariantViole):
        service.enregistrer(ecriture)
    assert service.grand_livre(DossierId("d1")) == ()
