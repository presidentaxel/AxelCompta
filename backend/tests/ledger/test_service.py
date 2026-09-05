from __future__ import annotations

import pytest

from axelcompta.ledger.service import LedgerService


def test_ledger_service_est_abstrait() -> None:
    with pytest.raises(TypeError):
        LedgerService()  # type: ignore[abstract]
