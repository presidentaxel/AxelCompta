"""UPDATE et DELETE refusés sur une décision et sur une signature."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from axelcompta.categorize.models import Etage
from axelcompta.core.ids import DossierId, EcritureId, TenantId, UserId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.workflow.decisions import DecisionHumaine
from axelcompta.workflow.decisions_postgres import PostgresDecisionRepository
from axelcompta.workflow.signature import DocumentSigne
from axelcompta.workflow.signature_postgres import PostgresSignatureRepository

pytestmark = pytest.mark.integration

BACKEND = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def migrations_appliquees(engine: Engine) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(cfg, "head")


def _dossier(engine: Engine, id_unique: str) -> None:
    depot = PostgresDossierRepository(engine)
    depot.enregistrer_tenant(Tenant(id=TenantId(id_unique), nom="T"))
    depot.enregistrer(
        Dossier(
            id=DossierId(id_unique),
            tenant_id=TenantId(id_unique),
            forme_juridique="SASU",
            regime_imposition="IS",
            regime_tva="reel_normal",
            nom="Test",
            tva_recettes_regime="franchise",
            exercice_debut=date(2026, 1, 1),
        )
    )


def test_update_d_une_decision_et_d_une_signature_est_refuse(
    engine: Engine, id_unique: str, migrations_appliquees: None
) -> None:
    _dossier(engine, id_unique)
    ecriture_id = f"{id_unique}-e1"
    PostgresLedgerService(engine).enregistrer(
        Ecriture(
            id=EcritureId(ecriture_id),
            dossier_id=DossierId(id_unique),
            journal=Journal.BQ,
            date=date(2026, 3, 1),
            libelle="Carburant",
            reference_piece=None,
            lignes=(
                LigneEcriture(compte="6061", sens=Sens.DEBIT, montant=Money(1000)),
                LigneEcriture(compte="512", sens=Sens.CREDIT, montant=Money(1000)),
            ),
        )
    )
    PostgresDecisionRepository(engine).enregistrer_decision(
        DecisionHumaine(
            dossier_id=DossierId(id_unique),
            ecriture_id=EcritureId(ecriture_id),
            categorie="carburant",
            etage_origine=Etage.REGLE,
            confiance_origine=0.9,
            decide_par=UserId("u1"),
            decide_le=datetime(2026, 9, 24, 10, 0, tzinfo=UTC),
        )
    )
    PostgresSignatureRepository(engine).enregistrer(
        DossierId(id_unique),
        "greffe_inpi",
        DocumentSigne(
            contenu_pdf=b"%PDF-1.4",
            signataire=UserId("u1"),
            signe_le=datetime(2026, 9, 24, 11, 0, tzinfo=UTC),
            provider="demo",
            qualifie=False,
        ),
    )
    with pytest.raises(DBAPIError):
        with engine.begin() as connexion:
            connexion.execute(
                text("UPDATE decisions_humaines SET categorie = 'autre' WHERE dossier_id = :id"),
                {"id": id_unique},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as connexion:
            connexion.execute(
                text("DELETE FROM documents_signes WHERE dossier_id = :id"),
                {"id": id_unique},
            )
