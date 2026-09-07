"""Comptes gestionnaire/chauffeur pour la démo, via Supabase Auth (doc 17
§9 bloc B, doc 19 §3). **Exception assumée à ADR-003** (« jamais Supabase
Auth ») — implémentation maison prévue en V1.

Composition root de démo comme `demo_api.py`/`demo_chauffeurs_type.py`
(doc 18) : intentionnellement **hors** du découpage `axelcompta/*` défini
en doc 03 §3, pas une nouvelle brique d'architecture. Étendre l'arbre
`tenants`/`api` pour un vrai module de comptes est une vraie décision de
structure (graphe de dépendances, contrat import-linter, doc 18) qui n'a
pas été prise ici — à faire quand on remplacera Supabase Auth par
l'implémentation maison (V1), pas avant.

Supabase est la **seule source de vérité** pour qui a été invité :
chaque utilisateur créé porte `user_metadata.dossier_id`, pas de table
séparée à synchroniser. Simplification assumée par rapport à doc 19 §3.2 :
seuls `non_invité` (absence d'utilisateur), `invité` (créé, e-mail non
confirmé) et `actif` (e-mail confirmé) sont modélisés. `compte_créé`
(onboarding partiel) et `inactif` (seuil d'usage, doc 19 §3.2 : « pas
bloquant pour la démo ») demanderaient un suivi applicatif que Supabase
Auth seul ne fournit pas — hors scope de ce premier découpage.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import httpx

from axelcompta.core.ids import DossierId


class StatutInvitation(Enum):
    INVITE = auto()
    ACTIF = auto()


@dataclass(frozen=True, slots=True)
class Invitation:
    dossier_id: DossierId
    email: str
    statut: StatutInvitation


class CompteDejaInviteError(ValueError):
    """Un compte existe déjà pour ce dossier — pas de double invitation
    silencieuse (doc 08 §2.7)."""


class CompteRepository(ABC):
    """Frontière vers le fournisseur de comptes — Supabase Auth pour la
    démo, implémentation maison prévue en V1 (doc 17 §9 bloc B)."""

    @abstractmethod
    def inviter(self, dossier_id: DossierId, email: str) -> Invitation:
        """Envoie une invitation réelle (e-mail). Lève `CompteDejaInviteError`
        si ce dossier a déjà un compte."""

    @abstractmethod
    def statut(self, dossier_id: DossierId) -> Invitation | None:
        """`None` si jamais invité pour ce dossier — c'est `non_invité`
        (doc 19 §3.2), représenté par l'absence plutôt qu'un état explicite."""


@dataclass(frozen=True, slots=True)
class SupabaseConfig:
    url: str
    service_role_key: str

    @staticmethod
    def depuis_env() -> SupabaseConfig:
        """Pas de valeur par défaut silencieuse (doc 08 §2.7) : les deux
        variables sont obligatoires ou on échoue tout de suite."""
        url = os.environ.get("SUPABASE_URL")
        cle = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not cle:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY manquantes (voir .env.example)"
            )
        return SupabaseConfig(url=url, service_role_key=cle)


class SupabaseCompteRepository(CompteRepository):
    def __init__(self, config: SupabaseConfig, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            base_url=f"{config.url}/auth/v1",
            headers={
                "apikey": config.service_role_key,
                "Authorization": f"Bearer {config.service_role_key}",
            },
            timeout=10.0,
        )

    def inviter(self, dossier_id: DossierId, email: str) -> Invitation:
        if self.statut(dossier_id) is not None:
            raise CompteDejaInviteError(f"dossier déjà invité : {dossier_id}")
        reponse = self._client.post(
            "/invite", json={"email": email, "data": {"dossier_id": dossier_id}}
        )
        reponse.raise_for_status()
        return Invitation(dossier_id=dossier_id, email=email, statut=StatutInvitation.INVITE)

    def statut(self, dossier_id: DossierId) -> Invitation | None:
        utilisateur = self._trouver_par_dossier(dossier_id)
        if utilisateur is None:
            return None
        confirme = utilisateur.get("email_confirmed_at") or utilisateur.get("confirmed_at")
        statut = StatutInvitation.ACTIF if confirme else StatutInvitation.INVITE
        return Invitation(dossier_id=dossier_id, email=utilisateur["email"], statut=statut)

    def _trouver_par_dossier(self, dossier_id: DossierId) -> dict[str, Any] | None:
        # `GET /admin/users` paginé côté Supabase mais pas de filtre serveur
        # par metadata — filtrage client, acceptable pour 3 dossiers de
        # démo, pas un choix qui tiendrait pour 200 dossiers réels (V1).
        reponse = self._client.get("/admin/users")
        reponse.raise_for_status()
        corps: dict[str, Any] = reponse.json()
        utilisateurs: list[dict[str, Any]] = corps.get("users", [])
        for utilisateur in utilisateurs:
            if utilisateur.get("user_metadata", {}).get("dossier_id") == dossier_id:
                return utilisateur
        return None
