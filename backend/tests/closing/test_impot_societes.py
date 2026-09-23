from __future__ import annotations

from datetime import date

from axelcompta.closing.impot_societes import arrondir_euros, calculer_is, plafond_taux_reduit

ANNEE = (date(2025, 1, 1), date(2025, 12, 31))


def test_taux_reduit_sous_le_plafond() -> None:
    calcul = calculer_is(1_234, *ANNEE)
    assert (calcul.base_taux_reduit, calcul.base_taux_normal) == (1_234, 0)
    assert calcul.impot == 185  # 185,10 arrondi à l'euro


def test_taux_normal_au_dela_de_42_500() -> None:
    calcul = calculer_is(50_000, *ANNEE)
    assert (calcul.base_taux_reduit, calcul.base_taux_normal) == (42_500, 7_500)
    assert calcul.impot == 6_375 + 1_875


def test_deficit_ou_resultat_nul_sans_impot() -> None:
    assert calculer_is(-500, *ANNEE).impot == 0
    assert calculer_is(0, *ANNEE).impot == 0


def test_plafond_proratise_sur_un_exercice_court() -> None:
    assert plafond_taux_reduit(*ANNEE) == 42_500
    # 06/01 → 31/12 : 360 jours, 42 500 × 360 / 365.
    assert plafond_taux_reduit(date(2025, 1, 6), date(2025, 12, 31)) == 41_918


def test_arrondi_commercial() -> None:
    assert arrondir_euros(1_346_50) == 1_347
    assert arrondir_euros(1_346_49) == 1_346
    assert arrondir_euros(-1_346_50) == -1_347
