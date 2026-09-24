"""Synchronisation Digifactory de tout un portefeuille (doc 16 §9).

Composition root comme `demo_api.py` et `demo_seed.py` (doc 18). Pas de
planificateur : tant que la file de jobs (ADR-002) n'existe pas, on lance ça à
la main ou depuis un cron. Chaque dossier est indépendant : l'échec de l'un
n'empêche pas les autres, et le code de sortie vaut 1 si l'un a échoué.

Usage, depuis backend/ (DATABASE_URL, DIGIFACTORY_BASE_URL et
DIGIFACTORY_TOKEN définis, migrations appliquées) :

    python -m axelcompta.synchro_digifactory --tenant <tenant_id>
    python -m axelcompta.synchro_digifactory --dossier <dossier_id>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime

from axelcompta.categorize.ml_fallback import ModeleMlIndisponible, charger_modele
from axelcompta.categorize.pipeline import CategorizationPipeline
from axelcompta.categorize.rules_and_ml import RulesAndMlPipeline
from axelcompta.core.db import engine_depuis_env
from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.consentement import classer, expiration_la_plus_proche
from axelcompta.ingestion.consentement_postgres import PostgresConsentementRepository
from axelcompta.ingestion.journal import JournalIngestion
from axelcompta.ingestion.journal_postgres import PostgresJournalIngestion
from axelcompta.ingestion.providers.digifactory import DigifactoryHttpClient, DigifactoryProvider
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.ledger.service import LedgerService
from axelcompta.packs.vtc_demo import charger_compte_par_categorie, charger_regles
from axelcompta.tenants.models import Dossier
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.workflow.propositions import PropositionRepository
from axelcompta.workflow.propositions_postgres import PostgresPropositionRepository
from axelcompta.workflow.synchro import RapportSynchro, SourceTransactions, synchroniser_dossier

SOURCE = "digifactory"


@dataclass(frozen=True, slots=True)
class ResultatDossier:
    dossier_id: DossierId
    rapport: RapportSynchro | None = None
    ignore: str | None = None  # raison, si le dossier n'a pas été traité
    erreur: str | None = None
    consentement: str | None = None


async def synchroniser_dossiers(
    dossiers: tuple[Dossier, ...],
    source: SourceTransactions,
    journal: JournalIngestion,
    ledger: LedgerService,
    propositions: PropositionRepository,
    pipeline: CategorizationPipeline,
    comptes: dict[str, str],
) -> list[ResultatDossier]:
    resultats: list[ResultatDossier] = []
    for dossier in dossiers:
        if dossier.contact_nr is None:
            resultats.append(ResultatDossier(dossier.id, ignore="pas de contact Digifactory"))
            continue
        try:
            rapport = await synchroniser_dossier(
                dossier, source, SOURCE, journal, ledger, propositions, pipeline, comptes
            )
        except Exception as exc:  # noqa: BLE001 — un dossier en échec ne bloque pas les autres
            resultats.append(ResultatDossier(dossier.id, erreur=f"{type(exc).__name__}: {exc}"))
        else:
            resultats.append(ResultatDossier(dossier.id, rapport=rapport))
    return resultats


def _afficher(resultat: ResultatDossier) -> None:
    if resultat.erreur:
        print(f"{resultat.dossier_id} : ECHEC {resultat.erreur}")
    elif resultat.ignore:
        print(f"{resultat.dossier_id} : ignoré ({resultat.ignore})")
    elif resultat.rapport:
        r = resultat.rapport
        print(
            f"{resultat.dossier_id} : {r.nouvelles} nouvelles ({r.a_trancher} à trancher), "
            f"{r.deja_connues} déjà connues, {r.modifiees_signalees} modifiées et "
            f"{r.supprimees_signalees} supprimées signalées, {r.rejets} rejetées"
            + (f", consentement {resultat.consentement}" if resultat.consentement else "")
        )


async def _relever_consentements(
    client: DigifactoryHttpClient,
    dossiers: tuple[Dossier, ...],
    resultats: list[ResultatDossier],
    depot: PostgresConsentementRepository,
    aujourd_hui: date,
) -> list[ResultatDossier]:
    """Après la synchro des transactions : lit `/accounts` et mémorise le
    statut. Un échec ici n'annule pas les écritures déjà posées."""
    releves: list[ResultatDossier] = []
    for dossier, resultat in zip(dossiers, resultats, strict=True):
        if dossier.contact_nr is None:
            expire_le = None
        else:
            try:
                payload = await client.accounts(dossier.contact_nr)
            except Exception as exc:  # noqa: BLE001 — le relevé ne doit pas effacer la synchro
                releves.append(resultat)
                print(f"{dossier.id} : consentement non relu ({type(exc).__name__})")
                continue
            expire_le = expiration_la_plus_proche(payload)
        statut = classer(expire_le, aujourd_hui)
        depot.enregistrer(dossier.id, expire_le, statut, datetime.now(UTC))
        releves.append(replace(resultat, consentement=statut.value))
    return releves


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    groupe = parseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--tenant")
    groupe.add_argument("--dossier")
    args = parseur.parse_args()

    engine = engine_depuis_env()
    depot = PostgresDossierRepository(engine)
    if args.dossier:
        dossier = depot.obtenir(DossierId(args.dossier))
        if dossier is None:
            print(f"Dossier inconnu : {args.dossier}", file=sys.stderr)
            return 1
        dossiers: tuple[Dossier, ...] = (dossier,)
    else:
        dossiers = depot.lister_par_tenant(TenantId(args.tenant))

    try:
        modele = charger_modele()
    except ModeleMlIndisponible:
        modele = None
    pipeline = RulesAndMlPipeline(regles=charger_regles(), modele=modele)

    async def lancer() -> list[ResultatDossier]:
        client = DigifactoryHttpClient.depuis_env()
        try:
            sante = await DigifactoryProvider(client_reel=client).health()
            if not sante.ok:
                print(f"Digifactory indisponible : {sante.message}", file=sys.stderr)
                return [ResultatDossier(d.id, erreur=sante.message) for d in dossiers]
            resultats = await synchroniser_dossiers(
                dossiers,
                DigifactoryProvider(client_reel=client),
                PostgresJournalIngestion(engine),
                PostgresLedgerService(engine),
                PostgresPropositionRepository(engine),
                pipeline,
                charger_compte_par_categorie(),
            )
            return await _relever_consentements(
                client, dossiers, resultats, PostgresConsentementRepository(engine), date.today()
            )
        finally:
            await client.aclose()

    resultats = asyncio.run(lancer())
    for resultat in resultats:
        _afficher(resultat)
    return 1 if any(r.erreur for r in resultats) else 0


if __name__ == "__main__":
    sys.exit(main())
