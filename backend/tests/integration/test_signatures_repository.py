"""PostgresSignatureRepository contre un vrai Postgres."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import Engine

from axelcompta.core.ids import DossierId, UserId
from axelcompta.workflow.signature import DocumentSigne
from axelcompta.workflow.signature_postgres import PostgresSignatureRepository

pytestmark = pytest.mark.integration


def _document(quand: datetime, pdf: bytes = b"%PDF-1.4 a") -> DocumentSigne:
    return DocumentSigne(
        contenu_pdf=pdf,
        signataire=UserId("u_test"),
        signe_le=quand,
        provider="demo",
        qualifie=False,
    )


def test_signature_enregistree_puis_relue(
    engine: Engine, id_unique: str, creer_dossier: Callable[[str], None]
) -> None:
    creer_dossier(id_unique)
    repo = PostgresSignatureRepository(engine)
    document = _document(datetime(2026, 9, 24, 10, 0, tzinfo=UTC))

    repo.enregistrer(DossierId(id_unique), "greffe_inpi", document)

    assert repo.dernier(DossierId(id_unique), "greffe_inpi") == document


def test_nouvelle_signature_devient_derniere_sans_effacer_historique(
    engine: Engine, id_unique: str, creer_dossier: Callable[[str], None]
) -> None:
    creer_dossier(id_unique)
    repo = PostgresSignatureRepository(engine)
    premiere = _document(datetime(2026, 9, 24, 10, 0, tzinfo=UTC), b"%PDF-1.4 un")
    seconde = _document(datetime(2026, 9, 24, 11, 0, tzinfo=UTC), b"%PDF-1.4 deux")
    repo.enregistrer(DossierId(id_unique), "greffe_inpi", premiere)
    repo.enregistrer(DossierId(id_unique), "greffe_inpi", seconde)

    assert repo.dernier(DossierId(id_unique), "greffe_inpi") == seconde
    assert repo.lister(DossierId(id_unique), "greffe_inpi") == (premiere, seconde)


def test_signatures_isolees_par_type_de_document(
    engine: Engine, id_unique: str, creer_dossier: Callable[[str], None]
) -> None:
    creer_dossier(id_unique)
    repo = PostgresSignatureRepository(engine)
    repo.enregistrer(
        DossierId(id_unique),
        "greffe_inpi",
        _document(datetime(2026, 9, 24, 10, 0, tzinfo=UTC)),
    )

    assert repo.dernier(DossierId(id_unique), "autre") is None
