"""Orchestration multi-dossiers de l'envoi de notifications."""

from __future__ import annotations

from datetime import date, datetime

from axelcompta.core.ids import DossierId, EcritureId, TenantId
from axelcompta.core.money import Money
from axelcompta.demo_comptes_memory import InMemoryCompteRepository
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens
from axelcompta.notifier import notifier_portefeuille
from axelcompta.tenants.models import Dossier
from axelcompta.workflow.decisions_memory import InMemoryDecisionRepository
from axelcompta.workflow.emails import Courriel, EmailSender
from axelcompta.workflow.notifications import InMemoryNotificationRepository

T0 = datetime(2026, 9, 22, 9, 0)


def _dossier(id_: str) -> Dossier:
    return Dossier(
        id=DossierId(id_),
        tenant_id=TenantId("t"),
        forme_juridique="SASU",
        regime_imposition="IS",
        regime_tva="reel_normal",
        nom=id_,
        tva_recettes_regime="franchise",
        exercice_debut=date(2026, 1, 1),
    )


def _ledger_avec_attente(*ids: str) -> InMemoryLedgerService:
    ledger = InMemoryLedgerService()
    m = Money(500)
    for id_ in ids:
        ledger.enregistrer(
            Ecriture(
                id=EcritureId(f"{id_}:1"),
                dossier_id=DossierId(id_),
                journal=Journal.BQ,
                date=date(2026, 3, 1),
                libelle="x",
                reference_piece=None,
                lignes=(
                    LigneEcriture(compte="512", sens=Sens.CREDIT, montant=m),
                    LigneEcriture(compte="471", sens=Sens.DEBIT, montant=m),
                ),
            )
        )
    return ledger


class _EnvoiQuiEchoueSurB(EmailSender):
    def __init__(self) -> None:
        self.envoyes: list[Courriel] = []

    def envoyer(self, courriel: Courriel) -> None:
        if courriel.destinataire.startswith("b@"):
            raise ConnectionError("smtp")
        self.envoyes.append(courriel)


def test_seuls_les_comptes_actifs_sont_notifies_et_un_echec_ne_bloque_pas_les_autres() -> None:
    comptes = InMemoryCompteRepository()
    for id_, email in (("a", "a@x.fr"), ("b", "b@x.fr"), ("c", "c@x.fr")):
        comptes.inviter(DossierId(id_), email)
    # « a » et « b » ont accepté leur invitation, « c » non ; « d » n'a jamais été invité.
    comptes._invitations[DossierId("a")] = _actif(comptes, "a")
    comptes._invitations[DossierId("b")] = _actif(comptes, "b")
    envoi = _EnvoiQuiEchoueSurB()

    resultats = notifier_portefeuille(
        tuple(_dossier(i) for i in "abcd"),
        _ledger_avec_attente("a", "b", "c", "d"),
        InMemoryDecisionRepository(),
        InMemoryNotificationRepository(),
        envoi,
        comptes,
        "https://app/login",
        T0,
    )

    statuts = {r.dossier_id: r.statut for r in resultats}
    assert statuts == {
        "a": "envoyee",
        "b": "echec",
        "c": "pas_de_compte_actif",
        "d": "pas_de_compte_actif",
    }
    assert [c.destinataire for c in envoi.envoyes] == ["a@x.fr"]


def _actif(comptes: InMemoryCompteRepository, id_: str):  # type: ignore[no-untyped-def]
    from axelcompta.demo_comptes import Invitation, StatutInvitation

    inv = comptes._invitations[DossierId(id_)]
    return Invitation(inv.dossier_id, inv.email, StatutInvitation.ACTIF)
