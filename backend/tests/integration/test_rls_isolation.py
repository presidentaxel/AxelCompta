"""Suite de tests d'isolation RLS (doc 12 §1.1, migration `87fc7238e52e`).

Contrairement aux autres tests d'intégration de ce dossier, celui-ci a
besoin des objets posés par Alembic en SQL brut (rôle, policies) — pas
seulement des tables (`metadata.create_all`, ce que fait la fixture
`engine` de `conftest.py`). D'où `command.upgrade(cfg, "head")` explicite,
comme `test_migrations.py`.

Le rôle `axelcompta_web` est un objet de *cluster* Postgres (partagé entre
`axelcompta_dev` et `axelcompta_test`, doc de la migration) : on le
retrouve tel quel, pas besoin de le créer ici, seulement une connexion qui
l'utilise sur la même base que l'`engine` (admin) de la fixture.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import DBAPIError, ProgrammingError

from axelcompta.categorize.models import Etage
from axelcompta.core.ids import DossierId, EcritureId, TenantId, UserId
from axelcompta.core.money import Money
from axelcompta.core.rls import appliquer_rls, contexte_identite
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


def _config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    return cfg


@pytest.fixture
def migrations_appliquees(engine: Engine) -> None:
    """Rôle + policies ne sont posés qu'en SQL brut par Alembic (doc en
    tête de fichier) — indépendant de la fixture `engine` qui ne fait que
    `metadata.create_all`. Utilisé par toute fixture/test qui a besoin des
    tables ET du rôle web, pas seulement des tables."""
    command.upgrade(_config(), "head")


@pytest.fixture
def engine_web(engine: Engine, migrations_appliquees: None) -> Iterator[Engine]:
    """Même base que `engine` (admin), rôle `axelcompta_web` — celui que
    `demo_api.py` utilise en réalité (`DATABASE_URL_WEB`)."""
    url = make_url(str(engine.url)).set(username="axelcompta_web", password="web_password_dev")
    moteur = create_engine(url)
    yield moteur
    moteur.dispose()


@pytest.fixture
def deux_tenants_trois_dossiers(engine: Engine, migrations_appliquees: None) -> None:
    """Karim/Sophie chez le tenant A, Yanis chez le tenant B — de quoi
    prouver l'isolation à la fois entre indivs et entre portefeuilles."""
    depot = PostgresDossierRepository(engine)
    depot.enregistrer_tenant(Tenant(id=TenantId("tenant-a"), nom="A"))
    depot.enregistrer_tenant(Tenant(id=TenantId("tenant-b"), nom="B"))
    for dossier_id, tenant_id in (
        ("karim", "tenant-a"),
        ("sophie", "tenant-a"),
        ("yanis", "tenant-b"),
    ):
        depot.enregistrer(
            Dossier(
                id=DossierId(dossier_id),
                tenant_id=TenantId(tenant_id),
                forme_juridique="SASU",
                regime_imposition="IS",
                regime_tva="reel_normal",
                nom=dossier_id,
                tva_recettes_regime="franchise",
                exercice_debut=date(2026, 1, 1),
            )
        )
        PostgresLedgerService(engine).enregistrer(
            Ecriture(
                id=EcritureId(f"{dossier_id}-1"),
                dossier_id=DossierId(dossier_id),
                journal=Journal.BQ,
                date=date(2026, 3, 1),
                libelle="test",
                reference_piece=None,
                lignes=(
                    LigneEcriture(compte="512", sens=Sens.CREDIT, montant=Money(1000)),
                    LigneEcriture(compte="471", sens=Sens.DEBIT, montant=Money(1000)),
                ),
            )
        )


def _dossiers_visibles(
    engine_web: Engine, dossier_id: str | None, tenant_id: str | None
) -> set[str]:
    with contexte_identite(dossier_id=dossier_id, tenant_id=tenant_id):
        with engine_web.connect() as connexion:
            appliquer_rls(connexion)
            return {row.id for row in connexion.execute(text("SELECT id FROM dossiers"))}


def _nb_ecritures_visibles(
    engine_web: Engine, dossier_id: str | None, tenant_id: str | None
) -> int:
    with contexte_identite(dossier_id=dossier_id, tenant_id=tenant_id):
        with engine_web.connect() as connexion:
            appliquer_rls(connexion)
            return int(connexion.execute(text("SELECT count(*) FROM ecritures")).scalar_one())


def test_sans_contexte_rien_nest_visible(
    engine_web: Engine, deux_tenants_trois_dossiers: None
) -> None:
    assert _dossiers_visibles(engine_web, dossier_id=None, tenant_id=None) == set()
    assert _nb_ecritures_visibles(engine_web, dossier_id=None, tenant_id=None) == 0


def test_indiv_ne_voit_que_son_propre_dossier(
    engine_web: Engine, deux_tenants_trois_dossiers: None
) -> None:
    assert _dossiers_visibles(engine_web, dossier_id="karim", tenant_id=None) == {"karim"}
    assert _nb_ecritures_visibles(engine_web, dossier_id="karim", tenant_id=None) == 1


def test_gestionnaire_voit_tout_son_portefeuille_et_rien_dautre(
    engine_web: Engine, deux_tenants_trois_dossiers: None
) -> None:
    # Tenant A : karim + sophie, jamais yanis (tenant B).
    assert _dossiers_visibles(engine_web, dossier_id=None, tenant_id="tenant-a") == {
        "karim",
        "sophie",
    }
    assert _nb_ecritures_visibles(engine_web, dossier_id=None, tenant_id="tenant-a") == 2


def test_ecriture_dun_autre_dossier_jamais_dans_le_grand_livre(
    engine_web: Engine, deux_tenants_trois_dossiers: None
) -> None:
    """Le test qui compte vraiment : même si `PostgresLedgerService` ou une
    future route oublie un `WHERE dossier_id = ...`, la base ne rend pas
    les lignes d'un autre dossier — pas seulement une vérification sur le
    nombre de lignes, sur le contenu réel."""
    with contexte_identite(dossier_id="karim", tenant_id=None):
        with engine_web.connect() as connexion:
            appliquer_rls(connexion)
            libelles = {
                row.dossier_id
                for row in connexion.execute(text("SELECT dossier_id FROM ecritures"))
            }
    assert libelles == {"karim"}


def test_ecriture_liee_isolee_via_sa_transaction_parente(
    engine_web: Engine, deux_tenants_trois_dossiers: None
) -> None:
    """`lignes_ecriture` n'a pas de `dossier_id` propre (doc de la
    migration) : sa policy passe par `ecritures`, on vérifie que ça
    marche vraiment, pas seulement sur le papier."""
    with contexte_identite(dossier_id="karim", tenant_id=None):
        with engine_web.connect() as connexion:
            appliquer_rls(connexion)
            nb = connexion.execute(text("SELECT count(*) FROM lignes_ecriture")).scalar_one()
            assert nb == 2  # les 2 lignes de l'écriture de karim, jamais celles de yanis

    with contexte_identite(dossier_id="yanis", tenant_id=None):
        with engine_web.connect() as connexion:
            appliquer_rls(connexion)
            nb = connexion.execute(text("SELECT count(*) FROM lignes_ecriture")).scalar_one()
            assert nb == 2


def test_ecrire_une_decision_hors_de_son_dossier_est_refuse(
    engine_web: Engine, deux_tenants_trois_dossiers: None
) -> None:
    """Le `WITH CHECK` protège aussi l'écriture, pas seulement la lecture :
    Sophie ne peut pas insérer une décision pour le dossier de Karim, même
    si un bug applicatif le tentait."""
    decision = DecisionHumaine(
        dossier_id=DossierId("karim"),
        ecriture_id=EcritureId("karim-1"),
        categorie="usage_personnel",
        etage_origine=Etage.REGLE,
        confiance_origine=0.9,
        decide_par=UserId("u1"),
        decide_le=datetime.now(UTC),
    )
    with contexte_identite(dossier_id="sophie", tenant_id=None):
        with pytest.raises((ProgrammingError, DBAPIError)):
            PostgresDecisionRepository(engine_web).enregistrer_decision(decision)


def test_signer_hors_de_son_dossier_est_refuse(
    engine_web: Engine, deux_tenants_trois_dossiers: None
) -> None:
    """Même barrière que les décisions : Sophie ne peut pas enregistrer une
    signature sur le dossier de Karim."""
    document = DocumentSigne(
        contenu_pdf=b"%PDF-1.4 demo",
        signataire=UserId("sophie"),
        signe_le=datetime.now(UTC),
        provider="demo",
        qualifie=False,
    )
    with contexte_identite(dossier_id="sophie", tenant_id=None):
        with pytest.raises((ProgrammingError, DBAPIError)):
            PostgresSignatureRepository(engine_web).enregistrer(
                DossierId("karim"), "greffe_inpi", document
            )


def test_le_role_administrateur_nest_jamais_soumis_aux_policies(
    engine: Engine, deux_tenants_trois_dossiers: None
) -> None:
    """`user` (celui de `demo_seed`/`synchro_digifactory`/`notifier`, doc
    de la migration) reste propriétaire des tables : les scripts
    d'administration continuent de voir tout le monde, sans contexte à
    poser — sinon `demo_seed` casserait au prochain amorçage."""
    with engine.connect() as connexion:
        assert connexion.execute(text("SELECT count(*) FROM dossiers")).scalar_one() == 3
