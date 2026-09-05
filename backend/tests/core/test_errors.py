from __future__ import annotations

import pytest

from axelcompta.core.errors import DomaineError, InvariantViole


def test_domaine_error_est_une_exception() -> None:
    with pytest.raises(DomaineError):
        raise DomaineError("erreur métier attendue")


def test_invariant_viole_est_distinct_de_domaine_error() -> None:
    assert not issubclass(InvariantViole, DomaineError)
