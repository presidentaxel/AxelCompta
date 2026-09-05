from __future__ import annotations

import pytest

from axelcompta.closing.service import ClosingService


def test_closing_service_est_abstrait() -> None:
    with pytest.raises(TypeError):
        ClosingService()  # type: ignore[abstract]
