from __future__ import annotations

import pytest

from axelcompta.closing.rubriques_2033 import (
    CHARGES_2033B,
    CompteSansRubrique,
    rubrique,
    rubrique_resultat,
    rubrique_selon_signe,
)


def test_prefixe_le_plus_long_l_emporte() -> None:
    assert rubrique("6712", CHARGES_2033B) == "300"
    assert rubrique("6061", CHARGES_2033B) == "242"
    assert rubrique("607", CHARGES_2033B) == "234"


def test_sens_des_comptes_de_resultat() -> None:
    assert rubrique_resultat("706") == ("218", -1)
    assert rubrique_resultat("645") == ("252", 1)
    assert rubrique_resultat("695") == ("306", 1)


def test_tous_les_comptes_60_a_79_ont_une_ligne() -> None:
    for classe in range(60, 80):
        rubrique_resultat(f"{classe}1")


def test_compte_inconnu_leve_une_erreur() -> None:
    with pytest.raises(CompteSansRubrique):
        rubrique_resultat("7")


def test_banque_et_tva_selon_le_signe() -> None:
    assert rubrique_selon_signe("512") == ("084", "156")
    assert rubrique_selon_signe("44551") == ("072", "172")
    assert rubrique_selon_signe("4551") == ("072", "173")
