"""PostgresDecisionRepository contre un vrai Postgres (doc 09 §4, doc 17 §9
bloc A)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.engine import Engine

from axelcompta.categorize.models import Etage
from axelcompta.core.db import metadata
from axelcompta.core.ids import DossierId, EcritureId, UserId
from axelcompta.workflow.decisions import AnnotationDev, DecisionHumaine
from axelcompta.workflow.decisions_postgres import PostgresDecisionRepository

pytestmark = pytest.mark.integration


def _decision(
    dossier_id: str, ecriture_id: str, categorie: str, decide_le: datetime
) -> DecisionHumaine:
    return DecisionHumaine(
        dossier_id=DossierId(dossier_id),
        ecriture_id=EcritureId(ecriture_id),
        categorie=categorie,
        etage_origine=Etage.REVUE_HUMAINE,
        confiance_origine=0.0,
        decide_par=UserId("u_test"),
        decide_le=decide_le,
    )


def test_decision_enregistree_puis_relue_comme_decision_courante(
    engine: Engine, id_unique: str
) -> None:
    metadata.create_all(engine)
    repo = PostgresDecisionRepository(engine)
    decision = _decision(id_unique, "e1", "usage_personnel", datetime(2026, 9, 7, 10, 0))

    repo.enregistrer_decision(decision)

    assert repo.decision_courante(DossierId(id_unique), EcritureId("e1")) == decision


def test_une_nouvelle_decision_devient_courante_sans_perdre_lhistorique(
    engine: Engine, id_unique: str
) -> None:
    metadata.create_all(engine)
    repo = PostgresDecisionRepository(engine)
    premiere = _decision(id_unique, "e1", "usage_personnel", datetime(2026, 9, 7, 10, 0))
    seconde = _decision(id_unique, "e1", "fournitures_administratives", datetime(2026, 9, 7, 11, 0))

    repo.enregistrer_decision(premiere)
    repo.enregistrer_decision(seconde)

    assert repo.decision_courante(DossierId(id_unique), EcritureId("e1")) == seconde
    assert repo.lister_decisions(DossierId(id_unique)) == (premiere, seconde)


def test_annotation_dev_persistee_sans_toucher_la_decision(engine: Engine, id_unique: str) -> None:
    metadata.create_all(engine)
    repo = PostgresDecisionRepository(engine)
    decision = _decision(id_unique, "e1", "usage_personnel", datetime(2026, 9, 7, 10, 0))
    repo.enregistrer_decision(decision)

    annotation = AnnotationDev(
        dossier_id=DossierId(id_unique),
        ecriture_id=EcritureId("e1"),
        juste=False,
        note="Devrait être fournitures_administratives",
        annote_par=UserId("u_dev"),
        annote_le=datetime(2026, 9, 8, 9, 0),
    )
    repo.enregistrer_annotation(annotation)

    assert repo.decision_courante(DossierId(id_unique), EcritureId("e1")) == decision
    assert repo.lister_annotations(DossierId(id_unique)) == (annotation,)


def test_decision_courante_dune_ecriture_jamais_tranchee_est_none(
    engine: Engine, id_unique: str
) -> None:
    metadata.create_all(engine)
    repo = PostgresDecisionRepository(engine)
    assert repo.decision_courante(DossierId(id_unique), EcritureId("inconnue")) is None
