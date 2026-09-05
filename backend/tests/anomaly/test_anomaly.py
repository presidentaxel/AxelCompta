from __future__ import annotations

import axelcompta.anomaly as anomaly


def test_le_module_documente_son_statut_non_prevu_pour_la_demo() -> None:
    assert anomaly.__doc__ and "démo" in anomaly.__doc__
