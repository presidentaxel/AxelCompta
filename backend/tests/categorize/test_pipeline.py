from __future__ import annotations

import pytest

from axelcompta.categorize.pipeline import CategorizationPipeline


def test_categorization_pipeline_est_abstrait() -> None:
    with pytest.raises(TypeError):
        CategorizationPipeline()  # type: ignore[abstract]
