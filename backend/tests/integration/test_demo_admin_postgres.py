"""Remise à neuf de la démo sur un vrai Postgres : seules les parties
cochées partent, le grand livre reste, les verrous reviennent."""

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
from axelcompta.demo_admin import reinitialiser_demo
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


def _peupler(engine: Engine, id_unique: str) -> str:
    _dossier(engine, id_unique)
    ecriture_id = f"{id_unique}-e1"
    PostgresLedgerService(engine).enregistrer(
        Ecriture(
            id=EcritureId(ecriture_id),
            dossier_id=DossierId(id_unique),
            journal=Journal.BQ,
            date=date(2026, 3, 1),
            libelle="Zara",
            reference_piece=None,
            lignes=(
                LigneEcriture(compte="471", sens=Sens.DEBIT, montant=Money(6000)),
                LigneEcriture(compte="512", sens=Sens.CREDIT, montant=Money(6000)),
            ),
        )
    )
    PostgresDecisionRepository(engine).enregistrer_decision(
        DecisionHumaine(
            dossier_id=DossierId(id_unique),
            ecriture_id=EcritureId(ecriture_id),
            categorie="usage_personnel",
            etage_origine=Etage.REGLE,
            confiance_origine=0.4,
            decide_par=UserId("u1"),
            decide_le=datetime(2026, 9, 25, 10, 0, tzinfo=UTC),
        )
    )
    PostgresSignatureRepository(engine).enregistrer(
        DossierId(id_unique),
        "greffe_inpi",
        DocumentSigne(
            contenu_pdf=b"%PDF-1.4",
            signataire=UserId("u1"),
            signe_le=datetime(2026, 9, 25, 11, 0, tzinfo=UTC),
            provider="demo",
            qualifie=False,
        ),
    )
    with engine.begin() as connexion:
        connexion.execute(
            text("UPDATE tenants SET nom = 'Renommé' WHERE id = :id"), {"id": id_unique}
        )
    return ecriture_id


def _compte(engine: Engine, table: str, id_unique: str) -> int:
    with engine.connect() as connexion:
        return int(
            connexion.execute(
                text(f"SELECT count(*) FROM {table} WHERE dossier_id = :id"), {"id": id_unique}
            ).scalar_one()
        )


def test_remise_a_neuf_efface_les_parties_cochees_et_garde_le_reste(
    engine: Engine, id_unique: str, migrations_appliquees: None, tmp_path: Path
) -> None:
    _peupler(engine, id_unique)
    (tmp_path / id_unique).mkdir()
    (tmp_path / id_unique / "photo.jpg").write_bytes(b"jpg")

    dossiers = reinitialiser_demo(
        engine, TenantId(id_unique), frozenset({"decisions", "justificatifs"}), tmp_path
    )

    assert dossiers == [id_unique]
    assert _compte(engine, "decisions_humaines", id_unique) == 0
    assert _compte(engine, "documents_signes", id_unique) == 1
    assert len(PostgresLedgerService(engine).grand_livre(DossierId(id_unique))) == 1
    assert not (tmp_path / id_unique).exists()
    with engine.connect() as connexion:
        nom = connexion.execute(
            text("SELECT nom FROM tenants WHERE id = :id"), {"id": id_unique}
        ).scalar_one()
    assert nom == "Renommé"


def test_les_verrous_reviennent_apres_la_remise_a_neuf(
    engine: Engine, id_unique: str, migrations_appliquees: None, tmp_path: Path
) -> None:
    _peupler(engine, id_unique)

    reinitialiser_demo(engine, TenantId(id_unique), frozenset({"jalons", "portefeuille"}), tmp_path)

    assert _compte(engine, "documents_signes", id_unique) == 0
    with engine.connect() as connexion:
        nom = connexion.execute(
            text("SELECT nom FROM tenants WHERE id = :id"), {"id": id_unique}
        ).scalar_one()
    assert nom == "Portefeuille démo"
    with pytest.raises(DBAPIError):
        with engine.begin() as connexion:
            connexion.execute(
                text("DELETE FROM decisions_humaines WHERE dossier_id = :id"), {"id": id_unique}
            )
