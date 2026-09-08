"""Vérification des jetons Supabase Auth côté chauffeur (doc 17 §9 bloc B,
« reste du bloc B », doc 19 §5.1-2).

Composition root de démo comme `demo_comptes.py`/`demo_api.py` (doc 18) :
intentionnellement **hors** du découpage `axelcompta/*` défini en doc 03
§3, pas une nouvelle brique d'architecture — même raisonnement que
`demo_comptes.py` (implémentation maison prévue en V1, ADR-003).

**Périmètre volontairement restreint (décidé avec Louis, 2026-09-08)** :
ce module authentifie le chauffeur, pas le gestionnaire. Le dashboard
gestionnaire reste sans login pour l'instant — `demo_api.UTILISATEUR_DEMO`
reste le stub pour l'action de tranchage gestionnaire (bloc C), en attente
d'un chantier d'auth gestionnaire qui n'est pas celui-ci. Ne pas confondre
« aucune identité fournie » (aujourd'hui : le gestionnaire, pas encore
authentifié) avec « identité invalide » (401) : le premier cas doit rester
silencieux tant que le gestionnaire n'a pas de compte, le second non.

**Découverte en testant contre le vrai projet Supabase (2026-09-08)** : ce
projet signe ses jetons en ES256 via les « JWT Signing Keys » (clé
asymétrique publiée en JWKS), pas en HS256 avec `SUPABASE_JWT_SECRET`. La
vérification de bloc B du 2026-09-07 (« un jeton signé à la main avec ce
secret est accepté par Supabase ») testait autre chose — que Supabase
accepte ce secret comme preuve d'identité *envers ses propres routes*, pas
que les jetons qu'il *émet* soient signés avec. Les deux sont des
vérifications différentes ; seule celle-ci (2026-09-08, contre un vrai
jeton de connexion) fait foi pour ce module. En clair : `SUPABASE_JWT_SECRET`
n'est plus utilisée par ce module — la vérification se fait contre la clé
publique exposée par Supabase, aucun secret à connaître côté serveur pour
valider un jeton.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Header, HTTPException

from axelcompta.core.ids import DossierId, UserId

# ES256 : algorithme par défaut des « JWT Signing Keys » Supabase (constaté
# 2026-09-08). RS256 accepté aussi : configuration possible côté Supabase,
# le JWKS fait foi dans les deux cas — jamais HS256 (secret partagé, plus
# émis par ce projet).
_ALGORITHMES_SUPABASE = ["ES256", "RS256"]
_AUDIENCE_SUPABASE = "authenticated"
_SUFFIXE_JWKS = "/auth/v1/.well-known/jwks.json"


class JetonInvalideError(ValueError):
    """Jeton absent de contenu exploitable — signature/expiration invalide,
    ou compte Supabase valide mais sans `dossier_id` (pas un compte
    chauffeur, doc 19 §3 : chaque invité porte `user_metadata.dossier_id`)."""


@dataclass(frozen=True, slots=True)
class IdentiteAuthentifiee:
    user_id: UserId
    dossier_id: DossierId
    email: str


@lru_cache(maxsize=1)
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    """Un client par URL Supabase, mis en cache — `PyJWKClient` a son
    propre cache interne de clés en plus (le JWKS ne change quasiment
    jamais)."""
    return jwt.PyJWKClient(f"{supabase_url}{_SUFFIXE_JWKS}")


def _url_supabase_depuis_env() -> str:
    """Pas de valeur par défaut silencieuse (doc 08 §2.7) : la variable est
    obligatoire ou on échoue tout de suite."""
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise RuntimeError("SUPABASE_URL manquante (voir .env.example)")
    return url


def verifier_jwt(jeton: str, cle_verification: Any) -> IdentiteAuthentifiee:
    """Vérifie un jeton d'accès Supabase et en extrait l'identité chauffeur.
    `cle_verification` est la clé publique déjà résolue (production : via
    `_jwks_client`, tests : une clé EC de test) — séparé de la résolution
    réseau pour rester testable sans HTTP. Lève `JetonInvalideError` sur
    toute anomalie."""
    try:
        charge_utile: dict[str, Any] = jwt.decode(
            jeton,
            cle_verification,
            algorithms=_ALGORITHMES_SUPABASE,
            audience=_AUDIENCE_SUPABASE,
        )
    except jwt.PyJWTError as exc:
        raise JetonInvalideError(f"jeton invalide : {exc}") from exc

    dossier_id = charge_utile.get("user_metadata", {}).get("dossier_id")
    if not dossier_id:
        raise JetonInvalideError("compte sans dossier_id — pas un compte chauffeur")

    return IdentiteAuthentifiee(
        user_id=UserId(charge_utile["sub"]),
        dossier_id=DossierId(dossier_id),
        email=charge_utile.get("email", ""),
    )


def _identite_depuis_en_tete(authorization: str | None) -> IdentiteAuthentifiee | None:
    """`None` si aucun en-tête (cas gestionnaire actuel, doc ci-dessus) —
    401 explicite si l'en-tête est présent mais inexploitable, jamais une
    401 silencieuse confondue avec une absence d'authentification."""
    if authorization is None:
        return None
    prefixe = "Bearer "
    if not authorization.startswith(prefixe):
        raise HTTPException(status_code=401, detail="En-tête Authorization mal formé.")
    jeton = authorization.removeprefix(prefixe)
    try:
        client = _jwks_client(_url_supabase_depuis_env())
        cle = client.get_signing_key_from_jwt(jeton).key
        return verifier_jwt(jeton, cle)
    except (JetonInvalideError, jwt.PyJWTError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def identite_chauffeur_optionnelle(
    authorization: Annotated[str | None, Header()] = None,
) -> IdentiteAuthentifiee | None:
    """Dépendance FastAPI — voir `_identite_depuis_en_tete`."""
    return _identite_depuis_en_tete(authorization)
