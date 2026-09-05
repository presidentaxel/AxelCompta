from __future__ import annotations

from axelcompta.core.pcg import nature_depuis_compte


def test_nature_depuis_compte() -> None:
    assert nature_depuis_compte("6061") == "charge"
    assert nature_depuis_compte("706") == "produit"
    assert nature_depuis_compte("101") == "autre"
