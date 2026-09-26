"""Retenues à la source sur les dividendes et déclaration 2777."""

from __future__ import annotations

from datetime import date

from axelcompta.closing.dividendes import ecriture_retenues, retenues
from axelcompta.core.ids import DossierId
from axelcompta.ledger.invariants import verifier_equilibre


def test_retenues_de_2026_sur_10_000_euros() -> None:
    detail = retenues(10_000_00, date(2026, 5, 20), dispense_prelevement=False)
    assert detail.prelevement_forfaitaire == 1_280_00  # 12,8 %
    assert (detail.csg, detail.crds, detail.solidarite) == (1_060_00, 50_00, 750_00)
    assert detail.total_retenu == 3_140_00  # 31,4 %
    assert detail.net_a_virer == 6_860_00
    assert detail.echeance_2777 == date(2026, 6, 15)


def test_dispense_du_prelevement_forfaitaire_mais_jamais_des_sociaux() -> None:
    detail = retenues(10_000_00, date(2026, 5, 20), dispense_prelevement=True)
    assert detail.prelevement_forfaitaire == 0
    assert detail.total_retenu == 1_860_00


def test_verse_en_decembre_la_2777_est_due_en_janvier() -> None:
    assert retenues(100_00, date(2026, 12, 3), False).echeance_2777 == date(2027, 1, 15)


def test_l_ecriture_passe_les_retenues_du_457_au_4423() -> None:
    detail = retenues(10_000_00, date(2026, 5, 20), dispense_prelevement=False)
    ecriture = ecriture_retenues(DossierId("d"), 2025, detail)
    verifier_equilibre(ecriture)
    lignes = {(ligne.compte, ligne.sens.name, ligne.montant.centimes) for ligne in ecriture.lignes}
    assert lignes == {
        ("457", "DEBIT", 3_140_00),
        ("4423", "CREDIT", 3_140_00),
    }
