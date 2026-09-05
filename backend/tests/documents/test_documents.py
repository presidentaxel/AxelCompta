from __future__ import annotations

import axelcompta.documents as documents


def test_le_module_documente_son_statut_non_prevu_pour_la_demo() -> None:
    assert documents.__doc__ and "démo" in documents.__doc__
