"""Relances des connexions bancaires dans la cloche (doc 14 §2.3)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.consentement import ReleveConsentement, SanteConnexion
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.workflow.notifications import (
    TYPE_CONNEXION_A_REFAIRE,
    TYPE_CONNEXION_EXPIREE,
    TYPE_CONNEXION_J7,
    TYPE_CONNEXION_J14,
    InMemoryNotificationRepository,
    NotificationEnvoyee,
)
from axelcompta.workflow.relances_consentement import mode_effectif, notifier_consentement

EXPIRE = date(2026, 10, 31)
TENANT = Tenant(id=TenantId("t"), nom="Flotte")


def _dossier(relance: str | None = None) -> Dossier:
    return Dossier(
        id=DossierId("d"),
        tenant_id=TenantId("t"),
        forme_juridique="SASU",
        regime_imposition="IS",
        regime_tva="reel_normal",
        nom="Karim",
        tva_recettes_regime="assujetti_taux_reduit",
        exercice_debut=date(2026, 1, 1),
        relance_consentement=relance,
    )


def _releve(
    expire: date | None = EXPIRE, sante: SanteConnexion = SanteConnexion.OK
) -> ReleveConsentement:
    return ReleveConsentement(DossierId("d"), expire, sante, None, datetime(2026, 9, 27, 8, 0))


def _jour(j: date) -> datetime:
    return datetime(j.year, j.month, j.day, 9, 0)


def _types_envoyes(
    jours: list[date], releve: ReleveConsentement, dossier: Dossier | None = None
) -> list[tuple[date, str]]:
    notifications = InMemoryNotificationRepository()
    for jour in jours:
        notifier_consentement(dossier or _dossier(), TENANT, releve, notifications, _jour(jour))
    return [(n.envoye_le.date(), n.type) for n in notifications.historique]


def _chaque_jour(debut: date, fin: date) -> list[date]:
    return [debut + timedelta(days=i) for i in range((fin - debut).days + 1)]


def test_j14_j7_expiration_puis_tous_les_trois_jours() -> None:
    """Relancée chaque jour, comme le fait le cron : une notification par palier."""
    envoyes = _types_envoyes(_chaque_jour(date(2026, 10, 1), date(2026, 11, 7)), _releve())
    assert envoyes == [
        (date(2026, 10, 17), TYPE_CONNEXION_J14),
        (date(2026, 10, 24), TYPE_CONNEXION_J7),
        (date(2026, 10, 31), TYPE_CONNEXION_EXPIREE),
        (date(2026, 11, 3), TYPE_CONNEXION_EXPIREE),
        (date(2026, 11, 6), TYPE_CONNEXION_EXPIREE),
    ]


def test_arrivee_tardive_un_seul_message_du_palier_en_cours() -> None:
    """Premier relevé à J-3 : pas de rattrapage du J-14, seulement le J-7."""
    envoyes = _types_envoyes([date(2026, 10, 28), date(2026, 10, 29)], _releve())
    assert envoyes == [(date(2026, 10, 28), TYPE_CONNEXION_J7)]


def test_une_connexion_renouvelee_repart_sur_un_nouveau_cycle() -> None:
    notifications = InMemoryNotificationRepository()
    notifier_consentement(_dossier(), TENANT, _releve(), notifications, _jour(date(2026, 10, 18)))
    renouvelee = _releve(expire=date(2027, 1, 29))
    for jour in (date(2026, 10, 20), date(2027, 1, 15)):
        notifier_consentement(_dossier(), TENANT, renouvelee, notifications, _jour(jour))
    assert [(n.envoye_le.date(), n.type) for n in notifications.historique] == [
        (date(2026, 10, 18), TYPE_CONNEXION_J14),
        (date(2027, 1, 15), TYPE_CONNEXION_J14),
    ]


def test_connexion_a_refaire_tous_les_trois_jours() -> None:
    releve = _releve(sante=SanteConnexion.AUTH_REQUISE)
    envoyes = _types_envoyes(_chaque_jour(date(2026, 9, 27), date(2026, 10, 3)), releve)
    assert envoyes == [
        (date(2026, 9, 27), TYPE_CONNEXION_A_REFAIRE),
        (date(2026, 9, 30), TYPE_CONNEXION_A_REFAIRE),
        (date(2026, 10, 3), TYPE_CONNEXION_A_REFAIRE),
    ]


def test_en_mode_manuel_rien_ne_part_au_chauffeur() -> None:
    assert _types_envoyes([date(2026, 10, 31)], _releve(), _dossier("manuel")) == []
    manuel = Tenant(id=TenantId("t"), relance_consentement="manuel")
    notifications = InMemoryNotificationRepository()
    notifier_consentement(_dossier(), manuel, _releve(), notifications, _jour(date(2026, 10, 31)))
    assert notifications.historique == []


def test_l_exception_du_dossier_prime_sur_le_portefeuille() -> None:
    manuel = Tenant(id=TenantId("t"), relance_consentement="manuel")
    assert mode_effectif(_dossier("auto"), manuel) == "auto"
    assert mode_effectif(_dossier(), manuel) == "manuel"
    assert mode_effectif(_dossier(), None) == "auto"


def test_rien_sans_releve_ni_expiration_lointaine() -> None:
    assert _types_envoyes([date(2026, 10, 1)], _releve()) == []
    assert _types_envoyes([date(2026, 10, 1)], _releve(expire=None)) == []
    notifications = InMemoryNotificationRepository()
    notifier_consentement(_dossier(), TENANT, None, notifications, _jour(date(2026, 10, 31)))
    assert notifications.historique == []


def test_le_message_est_lisible_dans_la_cloche() -> None:
    notification = NotificationEnvoyee(
        "n", DossierId("d"), TYPE_CONNEXION_J7, datetime(2026, 10, 24), ()
    )
    assert notification.message.startswith("Votre connexion bancaire expire dans une semaine")
