"""Affectation du résultat : réserve légale, distribuable, scénarios de
dividendes et écriture. Chiffres recalculés à la main dans les commentaires."""

from __future__ import annotations

from datetime import date

import pytest

from axelcompta.closing.affectation import (
    MillesimeDividendesInconnu,
    SituationAffectation,
    chiffrer,
    distribuable,
    dotation_reserve_legale,
    ecriture_affectation,
    scenarios,
)
from axelcompta.core.ids import DossierId
from axelcompta.ledger.invariants import verifier_equilibre

SASU = SituationAffectation(
    resultat=20_000_00,
    capital=1_000_00,
    reserve_legale=0,
    report_a_nouveau=0,
    tresorerie=25_000_00,
    dettes=3_000_00,
    charges_mensuelles=1_500_00,
    gerant_non_salarie=False,
    annee_versement=2026,
)


def _avec(**champs: object) -> SituationAffectation:
    import dataclasses

    return dataclasses.replace(SASU, **champs)  # type: ignore[arg-type]


def test_reserve_legale_plafonnee_a_dix_pour_cent_du_capital() -> None:
    # 5 % de 20 000 = 1 000, mais le plafond est 10 % de 1 000 = 100.
    assert dotation_reserve_legale(SASU) == 100_00
    assert dotation_reserve_legale(_avec(reserve_legale=100_00)) == 0
    # Gros capital : 5 % du résultat.
    assert dotation_reserve_legale(_avec(capital=100_000_00)) == 1_000_00


def test_distribuable_apres_pertes_anterieures_et_reserve() -> None:
    assert distribuable(SASU) == 19_900_00  # 20 000 - 100
    # 5 000 de pertes : base 15 000, réserve min(750, 100) = 100 -> 14 900.
    assert distribuable(_avec(report_a_nouveau=-5_000_00)) == 14_900_00
    # Report créditeur de 2 000 : s'ajoute -> 21 900.
    assert distribuable(_avec(report_a_nouveau=2_000_00)) == 21_900_00
    assert distribuable(_avec(resultat=-3_000_00)) == 0


def test_dividendes_d_un_president_de_sasu_au_pfu_de_2026() -> None:
    scenario = chiffrer(SASU, "x", "x", 10_000_00)
    assert scenario.impot_revenu == 1_280_00  # 12,8 %
    assert scenario.prelevements_sociaux == 1_860_00  # 18,6 % en 2026
    assert scenario.net_percu == 6_860_00  # 10 000 - 31,4 %
    assert scenario.part_soumise_cotisations == 0
    # En 2025, prélèvements sociaux à 17,2 %.
    assert chiffrer(_avec(annee_versement=2025), "x", "x", 10_000_00).net_percu == 7_000_00


def test_gerant_non_salarie_la_part_au_dela_du_seuil_est_signalee_pas_chiffree() -> None:
    eurl = _avec(gerant_non_salarie=True)
    scenario = chiffrer(eurl, "x", "x", 10_000_00)
    # Seuil : 10 % de 1 000 = 100 ; 9 900 relèvent des cotisations TNS.
    assert scenario.part_soumise_cotisations == 9_900_00
    assert scenario.prelevements_sociaux == 18_60  # 18,6 % de 100 seulement


def test_scenarios_du_moins_au_plus_bornes_par_la_tresorerie() -> None:
    liste = scenarios(SASU)
    assert [s.cle for s in liste] == ["garder", "prudent", "moitie", "maximum"]
    # Disponible 25 000 - 3 000 = 22 000 ; plafond min(19 900, 22 000).
    assert liste[-1].dividendes == 19_900_00
    # Prudent : 22 000 - 3 × 1 500 = 17 500.
    assert liste[1].dividendes == 17_500_00
    assert liste[0].dividendes == 0 and liste[0].laisse_en_societe == 19_900_00
    peu_de_tresorerie = scenarios(_avec(tresorerie=8_000_00))
    assert peu_de_tresorerie[-1].dividendes == 5_000_00  # 8 000 - 3 000


def test_l_ecriture_solde_le_resultat_et_s_equilibre() -> None:
    ecriture = ecriture_affectation(DossierId("d"), 2025, date(2026, 3, 1), SASU, 10_000_00)
    verifier_equilibre(ecriture)
    montants = {
        (ligne.compte, ligne.sens.name): ligne.montant.centimes for ligne in ecriture.lignes
    }
    assert montants == {
        ("120", "DEBIT"): 20_000_00,
        ("1061", "CREDIT"): 100_00,
        ("457", "CREDIT"): 10_000_00,
        ("110", "CREDIT"): 9_900_00,
    }


def test_une_perte_part_en_report_a_nouveau_debiteur() -> None:
    perte = _avec(resultat=-3_000_00)
    ecriture = ecriture_affectation(DossierId("d"), 2025, date(2026, 3, 1), perte, 0)
    verifier_equilibre(ecriture)
    assert {(ligne.compte, ligne.sens.name) for ligne in ecriture.lignes} == {
        ("119", "DEBIT"),
        ("129", "CREDIT"),
    }


def test_refuse_plus_que_distribuable_ou_disponible() -> None:
    with pytest.raises(ValueError):
        ecriture_affectation(DossierId("d"), 2025, date(2026, 3, 1), SASU, 19_900_01)


def test_annee_de_versement_sans_taux_connus() -> None:
    with pytest.raises(MillesimeDividendesInconnu):
        chiffrer(_avec(annee_versement=2031), "x", "x", 100)
