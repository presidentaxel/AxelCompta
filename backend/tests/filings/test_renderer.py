from __future__ import annotations

import pytest

from axelcompta.filings.renderer import FilingRenderer


def test_filing_renderer_est_abstrait() -> None:
    with pytest.raises(TypeError):
        FilingRenderer()  # type: ignore[abstract]
