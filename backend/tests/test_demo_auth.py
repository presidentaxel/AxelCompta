"""Vérification des jetons Supabase (doc 17 §9 bloc B, demo_auth.py) —
jetons ES256 signés à la main avec une clé de test, jamais d'appel réseau.

ES256, pas HS256 : c'est ce que le vrai projet Supabase émet (JWT Signing
Keys, découvert 2026-09-08 en testant contre un vrai jeton — voir le
commentaire de module de `demo_auth.py`)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from axelcompta.demo_auth import (
    JetonInvalideError,
    identite_chauffeur_optionnelle,
    verifier_jwt,
)

_CLE_PRIVEE = ec.generate_private_key(ec.SECP256R1())
_CLE_PUBLIQUE = _CLE_PRIVEE.public_key()
_AUTRE_CLE_PRIVEE = ec.generate_private_key(ec.SECP256R1())  # pour simuler une mauvaise signature


def _jeton(
    *,
    dossier_id: str | None = "DEMO_karim",
    expire_dans: timedelta = timedelta(hours=1),
    cle_privee: ec.EllipticCurvePrivateKey = _CLE_PRIVEE,
) -> str:
    charge_utile = {
        "sub": "user-123",
        "email": "karim@example.com",
        "aud": "authenticated",
        "exp": datetime.now(UTC) + expire_dans,
    }
    if dossier_id is not None:
        charge_utile["user_metadata"] = {"dossier_id": dossier_id}
    return jwt.encode(charge_utile, cle_privee, algorithm="ES256")


def test_jeton_valide_donne_lidentite_attendue() -> None:
    identite = verifier_jwt(_jeton(), _CLE_PUBLIQUE)
    assert identite.user_id == "user-123"
    assert identite.dossier_id == "DEMO_karim"
    assert identite.email == "karim@example.com"


def test_jeton_expire_est_rejete() -> None:
    with pytest.raises(JetonInvalideError):
        verifier_jwt(_jeton(expire_dans=timedelta(hours=-1)), _CLE_PUBLIQUE)


def test_mauvaise_signature_est_rejetee() -> None:
    jeton = _jeton(cle_privee=_AUTRE_CLE_PRIVEE)
    with pytest.raises(JetonInvalideError):
        verifier_jwt(jeton, _CLE_PUBLIQUE)


def test_compte_sans_dossier_id_est_rejete() -> None:
    """Un compte Supabase valide mais sans dossier_id n'est pas un compte
    chauffeur (doc 19 §3) — ne doit jamais être traité comme tel."""
    with pytest.raises(JetonInvalideError):
        verifier_jwt(_jeton(dossier_id=None), _CLE_PUBLIQUE)


class _ClientJwksFactice:
    """Bouchon de `jwt.PyJWKClient` — la clé de test est renvoyée quel que
    soit le jeton, pas de résolution JWKS réelle (pas d'appel réseau dans
    la suite rapide, même logique que les autres dépendances de démo)."""

    def get_signing_key_from_jwt(self, jeton: str) -> SimpleNamespace:
        return SimpleNamespace(key=_CLE_PUBLIQUE)


def test_dependance_sans_en_tete_retourne_none() -> None:
    """Aucune identité fournie (cas gestionnaire actuel, pas de login) ne
    doit jamais lever d'erreur — c'est le comportement par défaut inchangé."""
    assert identite_chauffeur_optionnelle(None) is None


def test_dependance_avec_en_tete_valide_retourne_lidentite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import axelcompta.demo_auth as demo_auth

    monkeypatch.setenv("SUPABASE_URL", "https://exemple.supabase.co")
    monkeypatch.setattr(demo_auth, "_jwks_client", lambda url: _ClientJwksFactice())

    identite = demo_auth.identite_chauffeur_optionnelle(f"Bearer {_jeton()}")
    assert identite is not None
    assert identite.dossier_id == "DEMO_karim"


def test_dependance_avec_en_tete_invalide_leve_401(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    import axelcompta.demo_auth as demo_auth

    monkeypatch.setenv("SUPABASE_URL", "https://exemple.supabase.co")
    monkeypatch.setattr(demo_auth, "_jwks_client", lambda url: _ClientJwksFactice())

    with pytest.raises(HTTPException) as exc_info:
        demo_auth.identite_chauffeur_optionnelle("Bearer jeton-invalide")
    assert exc_info.value.status_code == 401


def test_dependance_sans_prefixe_bearer_leve_401(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setenv("SUPABASE_URL", "https://exemple.supabase.co")
    with pytest.raises(HTTPException) as exc_info:
        identite_chauffeur_optionnelle(_jeton())
    assert exc_info.value.status_code == 401
