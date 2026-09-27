from __future__ import annotations

import dataclasses
import re
from datetime import date

import pytest

from axelcompta.categorize.ml_fallback import Calibration
from axelcompta.categorize.models import Etage
from axelcompta.categorize.rules_and_ml import (
    CATEGORIE_PAR_DEFAUT,
    SEUIL_PROPOSITION_ML,
    RulesAndMlPipeline,
)
from axelcompta.core.ids import DossierId, TransactionId
from axelcompta.ingestion.providers.base import NormalizedTransaction
from axelcompta.packs.vtc_demo import RegleCategorisation

REGLES_TEST = (RegleCategorisation(re.compile(r"total|esso", re.IGNORECASE), "carburant", "haute"),)


def _transaction(libelle: str, montant_cts: int = -4_500) -> NormalizedTransaction:
    return NormalizedTransaction(
        id=TransactionId("tx1"),
        dossier_id=DossierId("d1"),
        date=date(2026, 9, 3),
        montant_cts=montant_cts,
        libelle=libelle,
        source_provider="fixture",
        raw_payload={},
    )


def test_une_regle_qui_matche_gagne_avec_sa_confiance() -> None:
    pipeline = RulesAndMlPipeline(regles=REGLES_TEST)
    proposition = pipeline.categoriser(DossierId("d1"), _transaction("CB TOTAL A6"))
    assert proposition.categorie == "carburant"
    assert proposition.etage is Etage.REGLE
    assert proposition.confiance == 0.95


def test_sans_regle_ni_modele_tombe_en_categorie_par_defaut() -> None:
    pipeline = RulesAndMlPipeline(regles=REGLES_TEST)
    proposition = pipeline.categoriser(DossierId("d1"), _transaction("VIREMENT INCONNU"))
    assert proposition.categorie == CATEGORIE_PAR_DEFAUT
    assert proposition.etage is Etage.ML
    assert proposition.confiance == 0.0


class _ModeleBidon:
    """Modèle sklearn minimal (predict/predict_proba) pour tester le
    branchement, sans dépendre du vrai .joblib (gitignoré)."""

    classes_ = ("carburant", "peage_stationnement")

    def predict(self, x: list[str]) -> list[str]:
        return ["peage_stationnement" for _ in x]

    def predict_proba(self, x: list[str]) -> list[list[float]]:
        return [[0.1, 0.87] for _ in x]


def test_sans_regle_avec_modele_utilise_la_prediction_ml() -> None:
    pipeline = RulesAndMlPipeline(regles=REGLES_TEST, modele=_ModeleBidon())
    proposition = pipeline.categoriser(DossierId("d1"), _transaction("SANEF A10"))
    assert proposition.categorie == "peage_stationnement"
    assert proposition.etage is Etage.ML
    assert proposition.confiance == pytest.approx(0.87)


class _ModeleHesitant:
    classes_ = ("carburant", "peage_stationnement")

    def predict(self, x: list[str]) -> list[str]:
        return ["peage_stationnement" for _ in x]

    def predict_proba(self, x: list[str]) -> list[list[float]]:
        return [[0.3, SEUIL_PROPOSITION_ML - 0.01] for _ in x]


def test_sous_le_seuil_le_modele_ne_propose_rien() -> None:
    """Mieux vaut « pas de proposition » qu'une catégorie fausse à confirmer
    d'un geste. La confiance du modèle reste tracée."""
    pipeline = RulesAndMlPipeline(regles=REGLES_TEST, modele=_ModeleHesitant())
    proposition = pipeline.categoriser(DossierId("d1"), _transaction("SANEF A10"))
    assert proposition.categorie == CATEGORIE_PAR_DEFAUT
    assert proposition.etage is Etage.ML
    assert proposition.confiance == pytest.approx(SEUIL_PROPOSITION_ML - 0.01)


def test_une_regle_de_sens_contraire_est_sautee() -> None:
    """« BOLT » sur un paiement sortant n'est pas une recette plateforme."""
    regles = (
        RegleCategorisation(re.compile(r"bolt", re.IGNORECASE), "recettes_plateformes", "haute"),
    )
    pipeline = RulesAndMlPipeline(regles=regles)
    sortie = pipeline.categoriser(DossierId("d1"), _transaction("BOLT.EU/O/2603", -1_500))
    assert sortie.categorie == CATEGORIE_PAR_DEFAUT
    entree = pipeline.categoriser(DossierId("d1"), _transaction("BOLT OPERATIONS", 42_000))
    assert entree.categorie == "recettes_plateformes"


def test_un_modele_calibre_propose_et_fixe_le_seuil_par_categorie() -> None:
    """Sous le seuil de proposition calibré, rien ; au-dessus, la proposition
    porte le seuil d'imputation de sa catégorie."""
    calibration = Calibration(
        x=(0.0, 1.0),
        y=(0.0, 1.0),
        seuil_proposition=0.9,
        seuil_imputation=0.95,
        classes_imputables=frozenset({"peage_stationnement"}),
    )
    pipeline = RulesAndMlPipeline(regles=(), modele=_ModeleBidon(), calibration=calibration)
    proposition = pipeline.categoriser(DossierId("d1"), _transaction("SANEF A10"))
    assert proposition.categorie == CATEGORIE_PAR_DEFAUT  # 0,87 < 0,9
    calibration_basse = dataclasses.replace(calibration, seuil_proposition=0.5)
    pipeline = RulesAndMlPipeline(regles=(), modele=_ModeleBidon(), calibration=calibration_basse)
    proposition = pipeline.categoriser(DossierId("d1"), _transaction("SANEF A10"))
    assert proposition.categorie == "peage_stationnement"
    assert proposition.seuil_imputation == 0.95
