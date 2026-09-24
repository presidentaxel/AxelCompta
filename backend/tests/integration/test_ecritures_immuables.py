"""Le trigger refuse UPDATE et DELETE sur une écriture déjà enregistrée."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from axelcompta.core.ids import DossierId, EcritureId, TenantId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.tenants.postgres import PostgresDossierRepository

pytestmark = pytest.mark.integration

BACKEND = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def migrations_appliquees(engine: Engine) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(cfg, "head")


def test_update_et_delete_d_une_ecriture_sont_refuses(
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
            regime_tva="reel_normal",
            nom="Test",
            tva_recettes_regime="franchise",
            exercice_debut=date(2026, 1, 1),
        )
    )
    ecriture_id = f"{id_unique}-e1"
    PostgresLedgerService(engine).enregistrer(
        Ecriture(
            id=EcritureId(ecriture_id),
            dossier_id=DossierId(id_unique),
            journal=Journal.BQ,
            date=date(2026, 9, 3),
            libelle="Carburant",
            reference_piece=None,
            lignes=(
                LigneEcriture(compte="6061", sens=Sens.DEBIT, montant=Money(1000)),
                LigneEcriture(compte="512", sens=Sens.CREDIT, montant=Money(1000)),
            ),
        )
    )
    with pytest.raises(DBAPIError):
        with engine.begin() as connexion:
            connexion.execute(
                text("UPDATE ecritures SET libelle = 'modifie' WHERE id = :id"),
                {"id": ecriture_id},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as connexion:
            connexion.execute(
                text("DELETE FROM lignes_ecriture WHERE ecriture_id = :id"),
                {"id": ecriture_id},
            )
