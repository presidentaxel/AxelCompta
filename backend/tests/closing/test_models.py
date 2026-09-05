from __future__ import annotations

from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId


def test_liasse_pivot_porte_ses_cases_par_code() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026", cases={"2065": 12_000})
    assert liasse.cases["2065"] == 12_000


def test_liasse_pivot_a_des_cases_vides_par_defaut() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026")
    assert liasse.cases == {}
