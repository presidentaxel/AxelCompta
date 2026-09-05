from __future__ import annotations

from pathlib import Path

import pytest

from axelcompta.categorize.ml_fallback import (
    CHEMIN_MODELE_PAR_DEFAUT,
    ModeleMlIndisponible,
    charger_modele,
    predire,
    texte_pour_modele,
)


def test_texte_pour_modele_ajoute_le_bucket_de_montant() -> None:
    # -45,00 € : signe négatif, log10(45) ≈ 1,65 -> bucket 1
    assert texte_pour_modele("CB TOTAL A6", -4_500) == "CB TOTAL A6 [M-1]"


def test_texte_pour_modele_montant_nul() -> None:
    assert texte_pour_modele("ECART ARRONDI", 0) == "ECART ARRONDI [M0]"


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
    assert isinstance(categorie, str) and categorie
    assert 0.0 <= confiance <= 1.0
