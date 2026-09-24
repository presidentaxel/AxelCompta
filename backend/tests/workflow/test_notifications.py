from __future__ import annotations

from datetime import date, datetime, timedelta

from axelcompta.categorize.models import Etage
from axelcompta.core.ids import DossierId, EcritureId, UserId
from axelcompta.core.money import Money
from axelcompta.ledger.contrepassation import contrepasser
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens
from axelcompta.workflow.decisions import DecisionHumaine
from axelcompta.workflow.decisions_memory import InMemoryDecisionRepository
from axelcompta.workflow.emails import EmailSender, InMemoryEmailSender
from axelcompta.workflow.notifications import (
    INTERVALLE_MIN,
    RAPPEL,
    InMemoryNotificationRepository,
    composer,
    ecritures_a_trancher,
    notifier_a_trancher,
)

D = DossierId("d1")
T0 = datetime(2026, 9, 22, 9, 0)
LIEN = "https://app.exemple.fr/chauffeur/login"


def _ecriture(id_: str, compte: str) -> Ecriture:
    m = Money(1000)
    return Ecriture(
        id=EcritureId(id_),
        dossier_id=D,
        journal=Journal.BQ,
        date=date(2026, 3, 1),
        libelle="secret",
        reference_piece=None,
        lignes=(
            LigneEcriture(compte="512", sens=Sens.CREDIT, montant=m),
            LigneEcriture(compte=compte, sens=Sens.DEBIT, montant=m),
        ),
    )


class Env:
    def __init__(self, adresse: str | None = "chauffeur@exemple.fr") -> None:
        self.ledger = InMemoryLedgerService()
        self.decisions = InMemoryDecisionRepository()
        self.notifs = InMemoryNotificationRepository()
        self.emails = InMemoryEmailSender()
        self.adresse = adresse
        self.ajouter("e1", "471")

    def ajouter(self, id_: str, compte: str) -> None:
        self.ledger.enregistrer(_ecriture(id_, compte))

    def trancher(self, id_: str) -> None:
        self.decisions.enregistrer_decision(
            DecisionHumaine(D, EcritureId(id_), "carburant", Etage.REGLE, 0.9, UserId("u"), T0)
        )

    def notifier(self, maintenant: datetime, emails: EmailSender | None = None):  # type: ignore[no-untyped-def]
        return notifier_a_trancher(
            D,
            self.ledger,
            self.decisions,
            self.notifs,
            emails or self.emails,
            lambda _d: self.adresse,
            LIEN,
            maintenant,
        )


def test_seules_les_ecritures_au_compte_dattente_sans_decision_comptent() -> None:
    env = Env()
    env.ajouter("e2", "6061")
    env.ajouter("e3", "471")
    env.trancher("e3")

    assert ecritures_a_trancher(env.ledger, env.decisions, D) == ("e1",)


def test_rien_a_signaler_ninvite_personne() -> None:
    env = Env()
    env.trancher("e1")

    assert env.notifier(T0).statut == "rien_a_faire"
    assert env.emails.envoyes == []


def test_premier_envoi_puis_pas_de_doublon_immediat() -> None:
    env = Env()

    assert env.notifier(T0).statut == "envoyee"
    assert env.notifier(T0 + timedelta(minutes=5)).statut == "deja_notifie"
    assert len(env.emails.envoyes) == 1


def test_un_email_regroupe_tout_ce_qui_attend() -> None:
    env = Env()
    env.ajouter("e2", "471")
    env.ajouter("e3", "471")

    env.notifier(T0)

    (courriel,) = env.emails.envoyes
    assert "3 opérations" in courriel.sujet
    assert courriel.destinataire == "chauffeur@exemple.fr"


def test_de_nouvelles_operations_declenchent_un_email_apres_lintervalle() -> None:
    env = Env()
    env.notifier(T0)
    env.ajouter("e2", "471")

    assert env.notifier(T0 + INTERVALLE_MIN - timedelta(minutes=1)).statut == "deja_notifie"
    assert env.notifier(T0 + INTERVALLE_MIN).statut == "envoyee"


def test_sans_nouveaute_un_seul_rappel_par_semaine() -> None:
    env = Env()
    env.notifier(T0)

    assert env.notifier(T0 + RAPPEL - timedelta(hours=1)).statut == "deja_notifie"
    assert env.notifier(T0 + RAPPEL).statut == "envoyee"
    assert env.notifier(T0 + RAPPEL + timedelta(days=1)).statut == "deja_notifie"


def test_pas_de_compte_actif_pas_denvoi_et_pas_denregistrement() -> None:
    env = Env(adresse=None)

    assert env.notifier(T0).statut == "pas_de_compte_actif"
    assert env.notifs.historique == []
    env.adresse = "chauffeur@exemple.fr"
    assert env.notifier(T0 + timedelta(minutes=1)).statut == "envoyee"


class _EnvoiQuiEchoue(EmailSender):
    def envoyer(self, courriel) -> None:  # type: ignore[no-untyped-def]
        raise ConnectionError("smtp indisponible")


def test_un_echec_denvoi_nest_pas_enregistre_et_se_retente() -> None:
    env = Env()

    resultat = env.notifier(T0, emails=_EnvoiQuiEchoue())

    assert resultat.statut == "echec"
    assert env.notifs.historique == []
    assert env.notifier(T0 + timedelta(minutes=1)).statut == "envoyee"


def test_le_message_ne_contient_ni_montant_ni_libelle() -> None:
    env = Env()
    env.notifier(T0)

    (courriel,) = env.emails.envoyes
    assert "secret" not in courriel.corps and "10,00" not in courriel.corps
    assert LIEN in courriel.corps


def test_singulier_et_pluriel() -> None:
    assert composer(1, LIEN).sujet == "Une opération attend votre confirmation"
    assert composer(4, LIEN).sujet == "4 opérations attendent votre confirmation"


def test_une_ecriture_contre_passee_ne_reste_pas_a_trancher() -> None:
    env = Env()
    env.ledger.enregistrer(contrepasser(_ecriture("e1", "471")))

    assert ecritures_a_trancher(env.ledger, env.decisions, D) == ()
