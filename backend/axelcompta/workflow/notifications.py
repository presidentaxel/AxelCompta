"""Notifier l'indiv quand des opérations attendent sa décision (doc 19 §5.2).

Le modèle du produit repose sur un traitement au fil de l'eau, pas sur une
revue de fin d'année : sans ce signal, la file de revue reste vide de
lecteurs. Règles, pensées pour ne pas harceler :

- un seul e-mail par dossier regroupe tout ce qui attend, jamais un par
  transaction ;
- il ne repart que s'il y a des opérations **nouvelles** depuis le dernier
  envoi, et pas avant `INTERVALLE_MIN` ;
- s'il ne s'est rien passé, un rappel unique par `RAPPEL` tant que ça attend ;
- le message ne contient aucun montant ni libellé (l'e-mail n'est pas un
  canal sûr pour de la donnée comptable), seulement le nombre et le lien ;
- l'envoi n'est enregistré qu'une fois réussi : un échec se retente au
  passage suivant.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.ledger.contrepassation import annulees
from axelcompta.ledger.service import LedgerService

from .decisions import DecisionRepository
from .emails import Courriel, EmailSender

TYPE_A_TRANCHER = "a_trancher"
COMPTE_ATTENTE = "471"
INTERVALLE_MIN = timedelta(hours=6)
RAPPEL = timedelta(days=7)


@dataclass(frozen=True, slots=True)
class NotificationEnvoyee:
    id: str
    dossier_id: DossierId
    type: str
    envoye_le: datetime
    ecriture_ids: tuple[EcritureId, ...]


class NotificationRepository(ABC):
    @abstractmethod
    def derniere(self, dossier_id: DossierId, type_: str) -> NotificationEnvoyee | None: ...

    @abstractmethod
    def enregistrer(self, notification: NotificationEnvoyee) -> None: ...


class InMemoryNotificationRepository(NotificationRepository):
    def __init__(self) -> None:
        self.historique: list[NotificationEnvoyee] = []

    def derniere(self, dossier_id: DossierId, type_: str) -> NotificationEnvoyee | None:
        candidates = [n for n in self.historique if n.dossier_id == dossier_id and n.type == type_]
        return max(candidates, key=lambda n: n.envoye_le, default=None)

    def enregistrer(self, notification: NotificationEnvoyee) -> None:
        self.historique.append(notification)


def ecritures_a_trancher(
    ledger: LedgerService, decisions: DecisionRepository, dossier_id: DossierId
) -> tuple[EcritureId, ...]:
    """Écritures au compte d'attente sans décision humaine, hors paires
    originale + contre-passation."""
    ecritures = ledger.grand_livre(dossier_id)
    exclues = {d.ecriture_id for d in decisions.lister_decisions(dossier_id)} | annulees(ecritures)
    return tuple(
        e.id
        for e in ecritures
        if e.id not in exclues and any(ligne.compte == COMPTE_ATTENTE for ligne in e.lignes)
    )


@dataclass(frozen=True, slots=True)
class ResultatNotification:
    dossier_id: DossierId
    statut: str  # envoyee | rien_a_faire | deja_notifie | pas_de_compte_actif | echec
    nb_a_trancher: int = 0
    detail: str | None = None


def composer(nb: int, lien: str) -> Courriel:
    """Sans destinataire : posé par l'appelant. Deux textes distincts plutôt
    qu'un gabarit à trous, pour que le singulier se lise naturellement."""
    if nb == 1:
        sujet = "Une opération attend votre confirmation"
        constat = (
            "Un de vos derniers mouvements bancaires est resté sans catégorie : "
            "nous n'avons pas su le classer seuls. Vous le confirmez en quelques secondes."
        )
    else:
        sujet = f"{nb} opérations attendent votre confirmation"
        constat = (
            f"{nb} de vos derniers mouvements bancaires sont restés sans catégorie : "
            "nous n'avons pas su les classer seuls. Comptez quelques secondes chacun."
        )
    corps = (
        f"Bonjour,\n\n{constat}\nPlus vous confirmez tôt, plus votre comptabilité "
        f"reste à jour.\n\nOuvrir l'application : {lien}\n\nL'équipe AxeLCompta\n"
    )
    return Courriel(destinataire="", sujet=sujet, corps=corps)


def notifier_a_trancher(
    dossier_id: DossierId,
    ledger: LedgerService,
    decisions: DecisionRepository,
    notifications: NotificationRepository,
    emails: EmailSender,
    destinataire: Callable[[DossierId], str | None],
    lien_application: str,
    maintenant: datetime,
) -> ResultatNotification:
    en_attente = ecritures_a_trancher(ledger, decisions, dossier_id)
    if not en_attente:
        return ResultatNotification(dossier_id, "rien_a_faire")

    derniere = notifications.derniere(dossier_id, TYPE_A_TRANCHER)
    if derniere is not None:
        age = maintenant - derniere.envoye_le
        nouvelles = set(en_attente) - set(derniere.ecriture_ids)
        a_envoyer = (bool(nouvelles) and age >= INTERVALLE_MIN) or age >= RAPPEL
        if not a_envoyer:
            return ResultatNotification(dossier_id, "deja_notifie", len(en_attente))

    adresse = destinataire(dossier_id)
    if adresse is None:
        return ResultatNotification(dossier_id, "pas_de_compte_actif", len(en_attente))

    courriel = composer(len(en_attente), lien_application)
    try:
        emails.envoyer(Courriel(adresse, courriel.sujet, courriel.corps))
    except Exception as exc:  # noqa: BLE001 — à retenter au prochain passage
        return ResultatNotification(dossier_id, "echec", len(en_attente), f"{type(exc).__name__}")
    notifications.enregistrer(
        NotificationEnvoyee(
            id=uuid.uuid4().hex,
            dossier_id=dossier_id,
            type=TYPE_A_TRANCHER,
            envoye_le=maintenant,
            ecriture_ids=en_attente,
        )
    )
    return ResultatNotification(dossier_id, "envoyee", len(en_attente))
