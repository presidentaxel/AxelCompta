from __future__ import annotations

import re
from datetime import date

import pytest

from axelcompta.categorize.models import Etage
from axelcompta.categorize.rules_and_ml import CATEGORIE_PAR_DEFAUT, RulesAndMlPipeline
from axelcompta.core.ids import DossierId, TransactionId
from axelcompta.ingestion.providers.base import NormalizedTransaction
from axelcompta.packs.vtc_demo import RegleCategorisation

REGLES_TEST = (RegleCategorisation(re.compile(r"total|esso", re.IGNORECASE), "carburant", "haute"),)


def _transaction(libelle: str) -> NormalizedTransaction:
    return NormalizedTransaction(
        id=TransactionId("tx1"),
        dossier_id=DossierId("d1"),
        date=date(2026, 9, 3),
        montant_cts=-4_500,
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
