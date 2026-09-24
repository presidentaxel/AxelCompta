"""La contre-passation inverse les sens et ne touche pas à l'originale."""

from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.contrepassation import contrepasser
from axelcompta.ledger.invariants import verifier_equilibre
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens


def test_contrepassation_inverse_les_sens_et_reste_equilibree() -> None:
    origine = Ecriture(
        id=EcritureId("d1:digifactory-t1"),
        dossier_id=DossierId("d1"),
        journal=Journal.BQ,
        date=date(2026, 3, 1),
        libelle="CARTE TOTAL",
        reference_piece=None,
        lignes=(
            LigneEcriture(compte="6061", sens=Sens.DEBIT, montant=Money(6000)),
            LigneEcriture(compte="512", sens=Sens.CREDIT, montant=Money(6000)),
        ),
    )
    inverse = contrepasser(origine)
    assert inverse.id == EcritureId("d1:digifactory-t1:contrepassation")
    assert inverse.journal is Journal.OD
    assert inverse.reference_piece == "d1:digifactory-t1"
    assert [(ligne.compte, ligne.sens) for ligne in inverse.lignes] == [
        ("6061", Sens.CREDIT),
        ("512", Sens.DEBIT),
    ]
    verifier_equilibre(inverse)
    assert contrepasser(origine).id == inverse.id
