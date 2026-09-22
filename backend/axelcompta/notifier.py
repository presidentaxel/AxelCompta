"""Envoie aux indivs l'e-mail « des opérations attendent votre confirmation »
(doc 19 §5.2) pour tout un portefeuille.

Composition root comme `synchro_digifactory.py` (doc 18). Pas de
planificateur : à lancer depuis un cron, après la synchro. Les règles
anti-harcèlement (regroupement, intervalle, rappel) sont dans
`workflow/notifications.py` ; ce module ne fait que câbler.

Usage, depuis backend/ (DATABASE_URL, SUPABASE_URL,
SUPABASE_SERVICE_ROLE_KEY, SMTP_*, APP_BASE_URL définis) :

    python -m axelcompta.notifier --tenant <tenant_id>
    python -m axelcompta.notifier --tenant <tenant_id> --simulation
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

from axelcompta.core.db import engine_depuis_env
from axelcompta.core.ids import DossierId, TenantId
from axelcompta.demo_comptes import (
    CompteRepository,
    StatutInvitation,
    SupabaseCompteRepository,
    SupabaseConfig,
)
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.ledger.service import LedgerService
from axelcompta.tenants.models import Dossier
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.workflow.decisions import DecisionRepository
from axelcompta.workflow.decisions_postgres import PostgresDecisionRepository
from axelcompta.workflow.emails import EmailSender, InMemoryEmailSender, SmtpEmailSender
from axelcompta.workflow.notifications import (
    InMemoryNotificationRepository,
    NotificationRepository,
    ResultatNotification,
    notifier_a_trancher,
)
from axelcompta.workflow.notifications_postgres import PostgresNotificationRepository


def notifier_portefeuille(
    dossiers: tuple[Dossier, ...],
    ledger: LedgerService,
    decisions: DecisionRepository,
    notifications: NotificationRepository,
    emails: EmailSender,
    comptes: CompteRepository,
    lien_application: str,
    maintenant: datetime,
) -> list[ResultatNotification]:
    """Seuls les comptes **activés** (invitation acceptée) sont notifiés : un
    chauffeur invité qui n'a pas encore cliqué n'a pas d'application à
    ouvrir. Les comptes sont lus en un seul appel pour tout le portefeuille."""
    statuts = comptes.statuts([d.id for d in dossiers])
    adresses = {
        dossier_id: inv.email
        for dossier_id, inv in statuts.items()
        if inv.statut is StatutInvitation.ACTIF
    }
    resultats: list[ResultatNotification] = []
    for dossier in dossiers:
        try:
            resultats.append(
                notifier_a_trancher(
                    dossier.id,
                    ledger,
                    decisions,
                    notifications,
                    emails,
                    lambda d: adresses.get(d),
                    lien_application,
                    maintenant,
                )
            )
        except Exception as exc:  # noqa: BLE001 — un dossier en échec ne bloque pas les autres
            resultats.append(ResultatNotification(dossier.id, "echec", detail=type(exc).__name__))
    return resultats


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--tenant", required=True)
    parseur.add_argument(
        "--simulation",
        action="store_true",
        help="calcule et affiche sans envoyer ni enregistrer",
    )
    args = parseur.parse_args()

    lien = os.environ.get("APP_BASE_URL")
    if not lien:
        print("APP_BASE_URL manquante (voir .env.example)", file=sys.stderr)
        return 1
    engine = engine_depuis_env()
    dossiers = PostgresDossierRepository(engine).lister_par_tenant(TenantId(args.tenant))
    emails: EmailSender = InMemoryEmailSender() if args.simulation else SmtpEmailSender.depuis_env()
    notifications: NotificationRepository = (
        InMemoryNotificationRepository()
        if args.simulation
        else PostgresNotificationRepository(engine)
    )
    resultats = notifier_portefeuille(
        dossiers,
        PostgresLedgerService(engine),
        PostgresDecisionRepository(engine),
        notifications,
        emails,
        SupabaseCompteRepository(SupabaseConfig.depuis_env()),
        f"{lien.rstrip('/')}/chauffeur/login",
        datetime.now(UTC).replace(tzinfo=None),
    )
    for r in resultats:
        detail = f" ({r.detail})" if r.detail else ""
        print(f"{DossierId(r.dossier_id)} : {r.statut}, {r.nb_a_trancher} à trancher{detail}")
    return 1 if any(r.statut == "echec" for r in resultats) else 0


if __name__ == "__main__":
    sys.exit(main())
