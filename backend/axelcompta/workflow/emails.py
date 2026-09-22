"""Envoi d'e-mails transactionnels. Interface + SMTP standard, volontairement
sans SDK propriétaire (même règle anti-lock-in qu'ADR-003) : n'importe quel
fournisseur qui parle SMTP convient (Resend, Postmark, Scaleway...)."""

from __future__ import annotations

import os
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass(frozen=True, slots=True)
class Courriel:
    destinataire: str
    sujet: str
    corps: str


class EmailSender(ABC):
    @abstractmethod
    def envoyer(self, courriel: Courriel) -> None:
        """Lève en cas d'échec : l'appelant ne doit pas croire l'envoi fait."""


class InMemoryEmailSender(EmailSender):
    def __init__(self) -> None:
        self.envoyes: list[Courriel] = []

    def envoyer(self, courriel: Courriel) -> None:
        self.envoyes.append(courriel)


class SmtpEmailSender(EmailSender):
    def __init__(
        self, hote: str, port: int, utilisateur: str, mot_de_passe: str, expediteur: str
    ) -> None:
        self._hote = hote
        self._port = port
        self._utilisateur = utilisateur
        self._mot_de_passe = mot_de_passe
        self._expediteur = expediteur

    @classmethod
    def depuis_env(cls) -> SmtpEmailSender:
        """Pas de valeur par défaut silencieuse (doc 08 §2.7)."""
        manquantes = [
            nom
            for nom in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")
            if not os.environ.get(nom)
        ]
        if manquantes:
            raise RuntimeError(f"{', '.join(manquantes)} manquante(s) (voir .env.example)")
        return cls(
            os.environ["SMTP_HOST"],
            int(os.environ.get("SMTP_PORT", "587")),
            os.environ["SMTP_USER"],
            os.environ["SMTP_PASSWORD"],
            os.environ["SMTP_FROM"],
        )

    def envoyer(self, courriel: Courriel) -> None:
        message = EmailMessage()
        message["From"] = self._expediteur
        message["To"] = courriel.destinataire
        message["Subject"] = courriel.sujet
        message.set_content(courriel.corps)
        with smtplib.SMTP(self._hote, self._port, timeout=15) as serveur:
            serveur.starttls()
            serveur.login(self._utilisateur, self._mot_de_passe)
            serveur.send_message(message)
