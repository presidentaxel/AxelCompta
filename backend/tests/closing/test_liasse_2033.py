from __future__ import annotations

import pytest

from axelcompta.closing.liasse_2033 import (
    BilanDesequilibre,
    bilan,
    compte_de_resultat,
    net_actif,
    resultat_fiscal,
)
from axelcompta.closing.rubriques_2033 import CompteSansRubrique

# Balance d'une SASU : capital 1 000, CA 10 000, charges 6 000 dont 90 €
# d'amende, TVA due 800, IS 400 comptabilisé. Soldes débiteurs positifs.
BALANCE = {
    "1013": -1_000_00,
    "512": 5_800_00,
    "706": -10_000_00,
    "6061": 3_000_00,
    "645": 2_910_00,
    "6712": 90_00,
    "695": 400_00,
    "444": -400_00,
    "44551": -800_00,
}


def test_compte_de_resultat_par_rubrique() -> None:
    lignes = compte_de_resultat(BALANCE)
    assert lignes["218"] == 10_000
    assert (lignes["242"], lignes["252"], lignes["300"], lignes["306"]) == (3_000, 2_910, 90, 400)
    assert lignes["232"] == 10_000 and lignes["264"] == 5_910
    assert lignes["270"] == 4_090
    assert lignes["310"] == 10_000 - 5_910 - 90 - 400


def test_resultat_fiscal_reintegre_is_et_amendes() -> None:
    resultat = compte_de_resultat(BALANCE)
    fiscal = resultat_fiscal(resultat, BALANCE)
    assert fiscal["324"] == 400  # l'IS lui-même (notice, ligne 324)
    assert fiscal["330"] == 90  # CGI art. 39-2
    assert fiscal["312"] == 3_600 and fiscal["314"] == 0
    assert fiscal["352"] == fiscal["370"] == 3_600 + 400 + 90


def test_deficits_anterieurs_imputes_dans_la_limite_du_benefice() -> None:
    resultat = compte_de_resultat(BALANCE)
    fiscal = resultat_fiscal(resultat, BALANCE, deficits_anterieurs=10_000)
    assert fiscal["360"] == fiscal["352"]
    assert fiscal["370"] == 0


def test_bilan_equilibre_et_resultat_repris_en_136() -> None:
    resultat = compte_de_resultat(BALANCE)["310"]
    lignes = bilan(BALANCE, resultat)
    assert lignes["084"] == 5_800
    assert lignes["120"] == 1_000
    assert lignes["136"] == resultat
    assert lignes["172"] == 1_200 and lignes["169"] == 800
    assert lignes["110"] - lignes["112"] == lignes["180"] == 5_800
    assert net_actif(lignes)["110"] == 5_800


def test_decouvert_en_dettes_et_ecart_d_arrondi_absorbe() -> None:
    # 846,50 € de découvert, déficit -1 346,50 : 847 + (-1 347) + 500 = 0,
    # mais le résultat arrondi vaut -1 346 → 1 € d'écart à absorber.
    balance = {"1013": -500_00, "512": -846_50, "706": -100_00, "6061": 1_446_50}
    lignes = bilan(balance, -1_346)
    assert lignes["156"] == 846
    assert lignes["110"] - lignes["112"] == lignes["180"] == 0
    assert lignes["ECART_ARRONDI"] == -1


def test_compte_de_bilan_inconnu_leve_une_erreur() -> None:
    with pytest.raises(CompteSansRubrique):
        bilan({"25": 10_00, "1013": -10_00}, 0)


def test_bilan_faux_n_est_pas_masque_en_arrondi() -> None:
    with pytest.raises(BilanDesequilibre):
        bilan({"512": 100_000_00, "1013": -10_00}, 0)
