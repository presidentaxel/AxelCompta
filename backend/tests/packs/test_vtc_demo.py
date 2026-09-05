from __future__ import annotations

from axelcompta.packs.vtc_demo import (
    charger_compte_par_categorie,
    charger_regles,
    nature_depuis_compte,
)


def test_charge_les_regles_du_pack_reel() -> None:
    regles = charger_regles()
    assert len(regles) > 0
    assert any(r.categorie == "carburant" for r in regles)
    assert all(r.confiance in {"haute", "moyenne", "basse"} for r in regles)


def test_une_regle_matche_bien_un_libelle_carburant() -> None:
    regles = charger_regles()
    regle_carburant = next(r for r in regles if r.categorie == "carburant")
    assert regle_carburant.motif.search("CB TOTAL ACCESS A6 03/09")


def test_charge_un_compte_par_categorie() -> None:
    comptes = charger_compte_par_categorie()
    assert comptes["carburant"].startswith("6")
    assert comptes["recettes_plateformes"].startswith(("4", "7"))


def test_nature_depuis_compte() -> None:
    assert nature_depuis_compte("6061") == "charge"
    assert nature_depuis_compte("706") == "produit"
    assert nature_depuis_compte("101") == "autre"
