from __future__ import annotations

import axelcompta.ml as ml


def test_le_module_documente_labsence_dimport_au_runtime() -> None:
    assert ml.__doc__ and "runtime" in ml.__doc__
