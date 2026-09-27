from __future__ import annotations

from pathlib import Path

import pytest

from axelcompta.categorize.ml_fallback import (
    CHEMIN_MODELE_PAR_DEFAUT,
    ModeleMlIndisponible,
    charger_modele,
    predire,
    sens_compatible,
    texte_pour_modele,
)


def test_texte_pour_modele_ajoute_le_bucket_de_montant() -> None:
    # -45,00 € : signe négatif, log10(45) ≈ 1,65 -> bucket 1
    assert texte_pour_modele("CB TOTAL A6", -4_500) == "CB TOTAL A6 [M-1]"


def test_texte_pour_modele_montant_nul() -> None:
    assert texte_pour_modele("ECART ARRONDI", 0) == "ECART ARRONDI [M0]"


class _ModeleEspion:
    """Enregistre le texte reçu et renvoie des probabilités fixes."""

    def __init__(self, classes: tuple[str, ...], probabilites: list[float]) -> None:
        self.classes_ = classes
        self._probabilites = probabilites
        self.textes: list[str] = []

    def predict(self, x: list[str]) -> list[str]:
        raise AssertionError("predire() doit passer par predict_proba")

    def predict_proba(self, x: list[str]) -> list[list[float]]:
        self.textes.extend(x)
        return [self._probabilites for _ in x]


def test_le_montant_bancaire_est_retourne_dans_la_convention_d_entrainement() -> None:
    """Le modèle a appris sur le FEC (charge positive). Un encaissement
    bancaire de 1 190 € doit lui arriver comme une recette, en négatif."""
    espion = _ModeleEspion(("recettes_plateformes", "carburant"), [0.6, 0.4])
    predire(espion, "VIR RECU UBER", 119_000)
    predire(espion, "CB TOTAL A6", -4_500)
    assert espion.textes == ["VIR RECU UBER [M-3]", "CB TOTAL A6 [M+1]"]


def test_une_charge_n_est_jamais_proposee_pour_un_encaissement() -> None:
    espion = _ModeleEspion(("honoraires_comptable_juridique", "subventions"), [0.7, 0.2])
    categorie, confiance = predire(espion, "ABO COMPTA", 5_000)
    assert categorie == "subventions"
    assert confiance == pytest.approx(0.2)
    categorie, confiance = predire(espion, "ABO COMPTA", -5_000)
    assert categorie == "honoraires_comptable_juridique"
    assert confiance == pytest.approx(0.7)


def test_sens_compatible() -> None:
    assert not sens_compatible("recettes_plateformes", -100)
    assert not sens_compatible("carburant", 100)
    assert sens_compatible("frais_bancaires", 100)
    assert sens_compatible("frais_bancaires", -100)
    assert sens_compatible("carburant", 0)


def test_charger_modele_leve_si_fichier_absent(tmp_path: Path) -> None:
    with pytest.raises(ModeleMlIndisponible):
        charger_modele(tmp_path / "inexistant.joblib")


@pytest.mark.skipif(
    not CHEMIN_MODELE_PAR_DEFAUT.is_file(),
    reason="modèle .joblib non présent sur ce poste (gitignored, _AUDIT_DONNEES/modeles/)",
)
def test_contre_le_vrai_modele_si_present() -> None:
    modele = charger_modele()
    categorie, confiance = predire(modele, "CB TOTAL ACCESS A6", -4_500)
    assert categorie == "carburant"
    assert 0.0 <= confiance <= 1.0
    categorie, _ = predire(modele, "VIR RECU UBER BV", 119_000)
    assert sens_compatible(categorie, 119_000)
