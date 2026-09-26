"""Passage à l'exercice suivant de bout en bout sur Postgres : les
écritures d'inventaire et d'à-nouveaux passent par le vrai grand livre,
l'exercice clos et le dossier ouvert par les vrais dépôts."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.engine import Engine

from axelcompta.core.db import metadata
from axelcompta.core.ids import DossierId
from axelcompta.demo_seed import amorcer_demo
from axelcompta.exercices import executer_passage, preparer_passage
from axelcompta.ledger.models import Journal
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.tenants.exercices_postgres import PostgresExerciceRepository
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.workflow.decisions_postgres import PostgresDecisionRepository
from axelcompta.workflow.propositions_postgres import PostgresPropositionRepository

pytestmark = pytest.mark.integration
KARIM = DossierId("DEMO_karim")


def test_karim_passe_de_2025_a_2026_en_base(engine: Engine) -> None:
    metadata.create_all(engine)
    dossiers = PostgresDossierRepository(engine)
    ledger = PostgresLedgerService(engine)
    amorcer_demo(dossiers, ledger, PostgresPropositionRepository(engine))
    karim = dossiers.obtenir(KARIM)
    assert karim is not None
    decisions = PostgresDecisionRepository(engine)
    nb_avant = len(ledger.grand_livre(KARIM))

    passage = preparer_passage(karim, ledger, decisions, (), date(2026, 9, 26))
    executer_passage(
        passage, ledger, dossiers, PostgresExerciceRepository(engine), datetime(2026, 9, 26), "t"
    )
    executer_passage(  # reprise : rien en double
        passage, ledger, dossiers, PostgresExerciceRepository(engine), datetime(2026, 9, 26), "t"
    )

    grand_livre = ledger.grand_livre(KARIM)
    assert len(grand_livre) == nb_avant + 3
    (a_nouveaux,) = [e for e in grand_livre if e.reference_piece == "AN-2026"]
    assert a_nouveaux.journal is Journal.AN
    ouvert = dossiers.obtenir(KARIM)
    assert ouvert is not None and ouvert.exercice_debut == date(2026, 1, 1)
    assert [e.debut for e in PostgresExerciceRepository(engine).lister(KARIM)] == [date(2025, 1, 6)]
