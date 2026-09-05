from __future__ import annotations

import dataclasses

import pytest

from axelcompta.core.money import DevisesIncompatibles, Money


def test_money_stocke_des_centimes() -> None:
    montant = Money(centimes=12345)
    assert montant.centimes == 12345
    assert montant.devise == "EUR"


def test_money_est_immuable() -> None:
    montant = Money(centimes=100)
    with pytest.raises(dataclasses.FrozenInstanceError):
        montant.centimes = 200  # type: ignore[misc]


def test_addition_de_deux_money_meme_devise() -> None:
    assert Money(centimes=848_00) + Money(centimes=192_00) == Money(centimes=1_040_00)


def test_addition_refuse_les_devises_differentes() -> None:
    with pytest.raises(DevisesIncompatibles):
        Money(centimes=100, devise="EUR") + Money(centimes=100, devise="USD")


def test_somme_dun_tuple_vide_est_zero() -> None:
    assert Money.somme(()) == Money.zero()


def test_somme_cumule_plusieurs_montants() -> None:
    montants = (Money(centimes=100), Money(centimes=200), Money(centimes=300))
    assert Money.somme(montants) == Money(centimes=600)
