from __future__ import annotations

from axelcompta.packs.models import Pack


def test_pack_a_une_taxonomie_par_defaut_vide() -> None:
    pack = Pack(secteur="vtc", version="0.1")
    assert pack.categories == ()


def test_pack_porte_ses_categories() -> None:
    pack = Pack(secteur="vtc", version="0.1", categories=("carburant", "peage"))
    assert "carburant" in pack.categories
