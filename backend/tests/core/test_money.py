from __future__ import annotations

import dataclasses

import pytest

from axelcompta.core.money import Money


def test_money_stocke_des_centimes() -> None:
    montant = Money(centimes=12345)
    assert montant.centimes == 12345
    assert montant.devise == "EUR"


def test_money_est_immuable() -> None:
    montant = Money(centimes=100)
    with pytest.raises(dataclasses.FrozenInstanceError):
        montant.centimes = 200  # type: ignore[misc]
