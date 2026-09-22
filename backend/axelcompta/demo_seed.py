"""Amorçage de la base pour la démo : le portefeuille de démo, ses 3 dossiers,
leur ledger et les propositions du pipeline (doc 17 §4).

Composition root comme `demo_api.py` (doc 18). Avant le 2026-09-21, l'API
recalculait tout ça à chaque requête depuis `chauffeurs_demo.py` ; depuis,
elle lit Postgres, et ce module y écrit **une fois** ce que le pipeline
calculait à la volée. Ce sera aussi le point d'entrée des vrais dossiers du
pilote : mêmes tables, autre source de données (Digifactory, doc 16).

Usage, depuis backend/ (DATABASE_URL défini, migrations appliquées) :

    alembic upgrade head
    python -m axelcompta.demo_seed
"""

from __future__ import annotations

import dataclasses
import sys

from axelcompta.core.db import engine_depuis_env
from axelcompta.core.ids import EcritureId, TenantId
from axelcompta.demo_chauffeurs_type import construire_ledger
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO, ProfilChauffeurType
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.ledger.service import LedgerService
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.tenants.repository import DossierRepository
from axelcompta.workflow.propositions import PropositionRepository
from axelcompta.workflow.propositions_postgres import PostgresPropositionRepository

TENANT_DEMO = TenantId("TENANT_DEMO")


class AmorcageIncompletError(RuntimeError):
    """Le ledger d'un dossier existe mais est incomplet : un amorçage
    précédent a été interrompu. Pas de reprise silencieuse (doc 08 §2.7),
    on ne complète pas un ledger à moitié écrit."""


def _dossier_depuis_profil(profil: ProfilChauffeurType) -> Dossier:
    return Dossier(
        id=profil.dossier_id,
        tenant_id=TENANT_DEMO,
        forme_juridique=profil.forme_juridique,
        regime_imposition="IS",
        regime_tva="reel_normal",
        nom=profil.nom,
        tva_recettes_regime=profil.tva_recettes_regime,
        exercice_debut=profil.date_debut,
        plateformes=tuple(p.nom for p in profil.plateformes),
        mode_acces_bancaire=profil.mode_acces_bancaire,
    )


def _id_unique(dossier_id: str, ecriture_id: EcritureId) -> EcritureId:
    """Le pipeline numérote les écritures par dossier (`categorise-1`,
    `settlement-72`...) : deux dossiers produisent les mêmes ids. Les tables
    `ecritures` et `propositions_categorisation` ont l'id pour clé primaire,
    il doit donc être unique globalement. Préfixe par le dossier plutôt que
    d'imposer une clé composite à tout le ledger. `:` et non `/`, car l'id
    passe dans une URL (`/transactions/{ecriture_id}/decision`)."""
    return EcritureId(f"{dossier_id}:{ecriture_id}")


def amorcer_demo(
    dossiers: DossierRepository,
    ledger: LedgerService,
    propositions: PropositionRepository,
) -> list[str]:
    """Idempotent : un dossier dont le ledger est complet est laissé tel quel.
    Retourne les ids des dossiers effectivement écrits."""
    dossiers.enregistrer_tenant(Tenant(id=TENANT_DEMO, nom="Portefeuille démo"))
    ecrits: list[str] = []
    for profil in PROFILS_DEMO:
        dossiers.enregistrer(_dossier_depuis_profil(profil))
        ledger_calcule, props = construire_ledger(profil)
        attendues = ledger_calcule.grand_livre(profil.dossier_id)
        existantes = ledger.grand_livre(profil.dossier_id)
        if existantes:
            if len(existantes) != len(attendues):
                raise AmorcageIncompletError(
                    f"{profil.dossier_id} : {len(existantes)} écritures en base pour "
                    f"{len(attendues)} attendues. Vider les tables puis relancer."
                )
            continue
        for ecriture in attendues:
            ledger.enregistrer(
                dataclasses.replace(ecriture, id=_id_unique(profil.dossier_id, ecriture.id))
            )
        for ecriture_id, proposition in props.items():
            propositions.enregistrer(_id_unique(profil.dossier_id, ecriture_id), proposition)
        ecrits.append(profil.dossier_id)
    return ecrits


def main() -> int:
    engine = engine_depuis_env()
    ecrits = amorcer_demo(
        PostgresDossierRepository(engine),
        PostgresLedgerService(engine),
        PostgresPropositionRepository(engine),
    )
    if ecrits:
        print(f"Amorçage terminé : {', '.join(ecrits)}")
    else:
        print("Rien à faire : la base est déjà amorcée.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
