from __future__ import annotations

from datetime import date

from axelcompta.closing.liasse_2033_annexes import (
    immobilisations_2033c,
    mouvements,
    releve_2033d,
    valeur_ajoutee_2033e,
)
from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens


def _ecriture(journal: Journal, *lignes: tuple[str, Sens, int]) -> Ecriture:
    return Ecriture(
        id=EcritureId("e"),
        dossier_id=DossierId("d"),
        journal=journal,
        date=date(2025, 6, 1),
        libelle="",
        reference_piece=None,
        lignes=tuple(LigneEcriture(c, s, Money(m)) for c, s, m in lignes),
    )


def test_immobilisations_debut_augmentations_fin() -> None:
    m = mouvements(
        (
            _ecriture(
                Journal.AN, ("2182", Sens.DEBIT, 10_000_00), ("1013", Sens.CREDIT, 10_000_00)
            ),
            _ecriture(Journal.BQ, ("2182", Sens.DEBIT, 5_000_00), ("512", Sens.CREDIT, 5_000_00)),
            _ecriture(Journal.OD, ("6811", Sens.DEBIT, 3_000_00), ("28182", Sens.CREDIT, 3_000_00)),
        )
    )
    lignes = immobilisations_2033c(m)
    assert (lignes["460"], lignes["462"], lignes["464"], lignes["466"]) == (
        10_000,
        5_000,
        0,
        15_000,
    )
    assert lignes["492"] == 5_000 and lignes["496"] == 15_000
    assert (lignes["552"], lignes["556"], lignes["572"]) == (3_000, 3_000, 3_000)


def test_sans_immobilisation_le_2033c_est_neant() -> None:
    m = mouvements((_ecriture(Journal.BQ, ("512", Sens.DEBIT, 1_00), ("706", Sens.CREDIT, 1_00)),))
    assert immobilisations_2033c(m) == {}


def test_releve_2033d_tva_deficit_et_prelevements() -> None:
    balance = {"44571": -1_372_49, "44566": 464_44, "44562": 1_000_00}
    m = mouvements(
        (_ecriture(Journal.OD, ("455", Sens.DEBIT, 68_00), ("471", Sens.CREDIT, 68_00)),)
    )
    lignes = releve_2033d(balance, m, {"360": 0, "372": 1_256}, deficits_anterieurs=0)
    assert (lignes["374"], lignes["378"]) == (1_372, 464)  # 44562 : immobilisations, exclue
    assert lignes["399"] == 68
    assert lignes["860"] == lignes["870"] == 1_256


def test_valeur_ajoutee_sans_les_loyers_longue_duree() -> None:
    balance = {"706": -12_000_00, "6061": 3_000_00, "6226": 500_00, "613": 3_500_00}
    lignes = valeur_ajoutee_2033e(balance)
    assert lignes["108"] == lignes["106"] == 12_000
    assert (lignes["121"], lignes["125"]) == (3_000, 500)
    assert lignes["137"] == lignes["117"] == 8_500
    assert lignes["376"] == 0
