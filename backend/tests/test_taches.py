"""Enchaînement des tâches planifiées : synchro puis notifications, par
portefeuille, sans qu'une étape en échec n'empêche l'autre."""

from __future__ import annotations

from datetime import date

import pytest

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.synchro_digifactory import ResultatDossier
from axelcompta.taches import lancer_taches
from axelcompta.tenants.memory import InMemoryDossierRepository
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.workflow.notifications import ResultatNotification


def _depot(*dossiers: tuple[str, str, str | None]) -> InMemoryDossierRepository:
    depot = InMemoryDossierRepository()
    for id_, tenant, contact in dossiers:
        depot.enregistrer_tenant(Tenant(id=TenantId(tenant), nom=tenant))
        depot.enregistrer(
            Dossier(
                id=DossierId(id_),
                tenant_id=TenantId(tenant),
                forme_juridique="SASU",
                regime_imposition="IS",
                regime_tva="reel_normal",
                nom=id_,
                tva_recettes_regime="franchise",
                exercice_debut=date(2026, 1, 1),
                contact_nr=contact,
            )
        )
    return depot


def _notifier_tout(dossiers: tuple[Dossier, ...]) -> list[ResultatNotification]:
    return [ResultatNotification(d.id, "creee", 1) for d in dossiers]


class _Appels:
    def __init__(self) -> None:
        self.synchro: list[tuple[str, ...]] = []

    def synchroniser(self, dossiers: tuple[Dossier, ...]) -> list[ResultatDossier]:
        self.synchro.append(tuple(d.id for d in dossiers))
        return [ResultatDossier(d.id) for d in dossiers]


def test_un_portefeuille_sans_contact_digifactory_nest_pas_synchronise() -> None:
    appels = _Appels()
    depot = _depot(("a1", "A", None), ("b1", "B", "12"), ("b2", "B", None))

    bilan = lancer_taches(depot, appels.synchroniser, _notifier_tout)

    assert appels.synchro == [("b1", "b2")]
    assert bilan.lignes == [
        "A notifications : 1 créées, 0 en échec",
        "B synchro : 2 ok, 0 en échec",
        "B notifications : 2 créées, 0 en échec",
    ]
    assert not bilan.echec


def test_une_synchro_qui_plante_nempeche_pas_les_notifications() -> None:
    def planter(dossiers: tuple[Dossier, ...]) -> list[ResultatDossier]:
        raise ConnectionError("digifactory")

    bilan = lancer_taches(_depot(("b1", "B", "12")), planter, _notifier_tout)

    assert bilan.echec
    assert bilan.lignes[-1] == "B notifications : 1 créées, 0 en échec"


@pytest.mark.parametrize(
    ("resultat_synchro", "statut_notif"),
    [
        (ResultatDossier(DossierId("b1"), erreur="401"), "creee"),
        (ResultatDossier(DossierId("b1")), "echec"),
    ],
)
def test_un_dossier_en_echec_rend_le_passage_en_echec(
    resultat_synchro: ResultatDossier, statut_notif: str
) -> None:
    bilan = lancer_taches(
        _depot(("b1", "B", "12")),
        lambda _d: [resultat_synchro],
        lambda d: [ResultatNotification(x.id, statut_notif) for x in d],
    )

    assert bilan.echec


def test_sans_synchro_seules_les_notifications_passent() -> None:
    bilan = lancer_taches(_depot(("b1", "B", "12")), None, _notifier_tout)

    assert bilan.lignes == ["B notifications : 1 créées, 0 en échec"]
