"""Tâches planifiées : pour chaque portefeuille, synchro Digifactory puis
notifications internes (doc 12, J3 et J5).

Un seul point d'entrée pour le planificateur, quel qu'il soit : le crontab
du poste de Louis pour la démo, celui du serveur (ou un timer systemd) en
production, via `scripts/taches_planifiees.sh`. En attendant la file de
jobs (ADR-002), c'est ce module qui porte l'ordre des étapes.

Les notifications passent même si la synchro échoue : un dossier peut avoir
des opérations en attente depuis un passage précédent. Le code de sortie
vaut 1 dès qu'une étape a échoué quelque part, pour que le planificateur le
signale.

Usage, depuis backend/ (DATABASE_URL, DIGIFACTORY_BASE_URL et
DIGIFACTORY_TOKEN définis) :

    python -m axelcompta.taches
    python -m axelcompta.taches --sans-synchro
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from axelcompta.core.db import engine_depuis_env
from axelcompta.notifier import notifier_depuis_base
from axelcompta.synchro_digifactory import ResultatDossier, synchroniser_portefeuille
from axelcompta.tenants.models import Dossier
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.tenants.repository import DossierRepository
from axelcompta.workflow.notifications import ResultatNotification

Synchroniser = Callable[[tuple[Dossier, ...]], list[ResultatDossier]]
Notifier = Callable[[tuple[Dossier, ...]], list[ResultatNotification]]


@dataclass
class BilanTaches:
    lignes: list[str] = field(default_factory=list)
    echec: bool = False


def lancer_taches(
    depot: DossierRepository,
    synchroniser: Synchroniser | None,
    notifier: Notifier,
) -> BilanTaches:
    """`synchroniser` à None saute la synchro (`--sans-synchro`). Un
    portefeuille sans aucun contact Digifactory n'appelle pas Digifactory."""
    bilan = BilanTaches()
    for tenant in depot.lister_tenants():
        dossiers = depot.lister_par_tenant(tenant.id)
        if not dossiers:
            continue
        if synchroniser is not None and any(d.contact_nr for d in dossiers):
            try:
                resultats = synchroniser(dossiers)
            except Exception as exc:  # noqa: BLE001 — la notification passe quand même
                bilan.echec = True
                bilan.lignes.append(f"{tenant.id} synchro : échec ({type(exc).__name__}: {exc})")
            else:
                erreurs = [r for r in resultats if r.erreur]
                bilan.echec |= bool(erreurs)
                bilan.lignes.append(
                    f"{tenant.id} synchro : {len(resultats) - len(erreurs)} ok, "
                    f"{len(erreurs)} en échec"
                )
        notifs = notifier(dossiers)
        creees = sum(1 for r in notifs if r.statut == "creee")
        echecs = sum(1 for r in notifs if r.statut == "echec")
        bilan.echec |= echecs > 0
        bilan.lignes.append(f"{tenant.id} notifications : {creees} créées, {echecs} en échec")
    return bilan


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--sans-synchro", action="store_true")
    args = parseur.parse_args()

    debut = datetime.now(UTC)
    engine = engine_depuis_env()
    bilan = lancer_taches(
        PostgresDossierRepository(engine),
        None if args.sans_synchro else (lambda d: synchroniser_portefeuille(engine, d)),
        lambda d: notifier_depuis_base(engine, d),
    )
    print(f"[{debut.isoformat(timespec='seconds')}] tâches planifiées")
    for ligne in bilan.lignes:
        print(f"  {ligne}")
    return 1 if bilan.echec else 0


if __name__ == "__main__":
    sys.exit(main())
