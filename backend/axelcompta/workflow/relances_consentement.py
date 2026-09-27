"""Relances des connexions bancaires dans l'application (doc 14 §2.3).

En mode « auto », le chauffeur est prévenu dans la cloche de son espace, pas
par e-mail (Louis, 2026-09-26 : l'e-mail et le SMS sont des intégrations du
gestionnaire) : deux semaines avant l'expiration, une semaine avant, à
l'expiration, puis tous les 3 jours tant que la connexion n'est pas
renouvelée. Une connexion que la banque demande de confirmer (SCA à refaire)
est prévenue de la même façon, tous les 3 jours. En mode « manuel », rien ne
part : seul le gestionnaire voit l'état, et contacte ses chauffeurs.

Une seule notification par palier : relancer la tâche planifiée toutes les
heures ne répète rien.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from axelcompta.core.ids import DossierId
from axelcompta.ingestion.consentement import ReleveConsentement, SanteConnexion
from axelcompta.tenants.models import Dossier, Tenant

from .notifications import (
    TYPE_CONNEXION_A_REFAIRE,
    TYPE_CONNEXION_EXPIREE,
    TYPE_CONNEXION_J7,
    TYPE_CONNEXION_J14,
    NotificationEnvoyee,
    NotificationRepository,
    ResultatNotification,
)

PALIER_APRES_EXPIRATION = timedelta(days=3)


def mode_effectif(dossier: Dossier, tenant: Tenant | None) -> str:
    """L'exception du dossier, sinon le mode du portefeuille."""
    if dossier.relance_consentement is not None:
        return dossier.relance_consentement
    return tenant.relance_consentement if tenant is not None else "auto"


@dataclass(frozen=True, slots=True)
class Palier:
    type: str
    debut: date  # une notification de ce type avant cette date ne compte pas


def palier_du_jour(
    releve: ReleveConsentement, aujourd_hui: date, derniere_a_refaire: date | None
) -> Palier | None:
    """Le palier en cours, ou None s'il n'y a rien à dire aujourd'hui."""
    if releve.sante is SanteConnexion.AUTH_REQUISE:
        debut = (
            derniere_a_refaire + PALIER_APRES_EXPIRATION
            if derniere_a_refaire is not None
            else aujourd_hui
        )
        return Palier(TYPE_CONNEXION_A_REFAIRE, debut) if aujourd_hui >= debut else None
    if releve.expire_le is None:
        return None
    reste = (releve.expire_le - aujourd_hui).days
    if reste > 14:
        return None
    if reste > 7:
        return Palier(TYPE_CONNEXION_J14, releve.expire_le - timedelta(days=14))
    if reste > 0:
        return Palier(TYPE_CONNEXION_J7, releve.expire_le - timedelta(days=7))
    ecoules = -reste // PALIER_APRES_EXPIRATION.days * PALIER_APRES_EXPIRATION.days
    return Palier(TYPE_CONNEXION_EXPIREE, releve.expire_le + timedelta(days=ecoules))


def notifier_consentement(
    dossier: Dossier,
    tenant: Tenant | None,
    releve: ReleveConsentement | None,
    notifications: NotificationRepository,
    maintenant: datetime,
) -> ResultatNotification:
    type_par_defaut = TYPE_CONNEXION_J14
    if releve is None or mode_effectif(dossier, tenant) == "manuel":
        return ResultatNotification(dossier.id, "rien_a_faire", type=type_par_defaut)
    a_refaire = notifications.derniere(dossier.id, TYPE_CONNEXION_A_REFAIRE)
    palier = palier_du_jour(
        releve, maintenant.date(), a_refaire.envoye_le.date() if a_refaire else None
    )
    if palier is None:
        return ResultatNotification(dossier.id, "rien_a_faire", type=type_par_defaut)
    derniere = notifications.derniere(dossier.id, palier.type)
    if derniere is not None and derniere.envoye_le.date() >= palier.debut:
        return ResultatNotification(dossier.id, "deja_notifie", type=palier.type)
    notifications.enregistrer(
        NotificationEnvoyee(
            id=uuid.uuid4().hex,
            dossier_id=DossierId(dossier.id),
            type=palier.type,
            envoye_le=maintenant,
            ecriture_ids=(),
        )
    )
    return ResultatNotification(dossier.id, "creee", type=palier.type)
