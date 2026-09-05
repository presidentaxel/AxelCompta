from __future__ import annotations

import axelcompta.workflow as workflow


def test_le_module_documente_son_statut_non_prevu_pour_la_demo() -> None:
    assert workflow.__doc__ and "démo" in workflow.__doc__
