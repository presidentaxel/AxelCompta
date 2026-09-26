"""Une décision ou une signature laisse une ligne d'audit, jamais modifiable."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from axelcompta.core.ids import DossierId, TenantId, UserId
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.workflow.signature import DocumentSigne
from axelcompta.workflow.signature_postgres import PostgresSignatureRepository

pytestmark = pytest.mark.integration

BACKEND = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def migrations_appliquees(engine: Engine) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(cfg, "head")


def test_signature_ecrit_le_journal_et_le_journal_est_immuable(
    engine: Engine, id_unique: str, migrations_appliquees: None
) -> None:
    depot = PostgresDossierRepository(engine)
    depot.enregistrer_tenant(Tenant(id=TenantId(id_unique), nom="T"))
    depot.enregistrer(
        Dossier(
            id=DossierId(id_unique),
            tenant_id=TenantId(id_unique),
            forme_juridique="SASU",
            regime_imposition="IS",
            regime_tva="franchise",
            nom="Test",
            tva_recettes_regime="franchise",
            exercice_debut=date(2026, 1, 1),
        )
    )
    PostgresSignatureRepository(engine).enregistrer(
        DossierId(id_unique),
        "greffe_inpi",
        DocumentSigne(
            contenu_pdf=b"%PDF-1.4",
            signataire=UserId("u1"),
            signe_le=datetime(2026, 9, 24, 12, 0, tzinfo=UTC),
            provider="demo",
            qualifie=False,
        ),
    )
    with engine.connect() as connexion:
        ligne = connexion.execute(
            text("SELECT type_acte, acteur FROM journal_audit WHERE dossier_id = :id"),
            {"id": id_unique},
        ).one()
    assert (ligne.type_acte, ligne.acteur) == ("signature", "u1")
    with pytest.raises(DBAPIError):
        with engine.begin() as connexion:
            connexion.execute(
                text("DELETE FROM journal_audit WHERE dossier_id = :id"),
                {"id": id_unique},
            )
