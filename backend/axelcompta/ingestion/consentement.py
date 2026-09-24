"""Statut du consentement bancaire DSP2 (doc 14 §2.2).

Pur : aucune I/O. La date vient de `item.authentication_expires_at`
(doc 16 §3.2). À 14 jours ou moins, le dossier est à renouveler.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

DELAI_RENOUVELLEMENT = timedelta(days=14)
_SENTINELLE = "0000-00-00"


class StatutConsentement(Enum):
    JAMAIS_CONNECTE = "jamais_connecte"
    EXPIRE = "expire"
    A_RENOUVELER = "a_renouveler"
    ACTIF = "actif"


def classer(expire_le: date | None, aujourd_hui: date) -> StatutConsentement:
    if expire_le is None:
        return StatutConsentement.JAMAIS_CONNECTE
    if expire_le < aujourd_hui:
        return StatutConsentement.EXPIRE
    if expire_le <= aujourd_hui + DELAI_RENOUVELLEMENT:
        return StatutConsentement.A_RENOUVELER
    return StatutConsentement.ACTIF


def _date_expiration(valeur: object) -> date | None:
    if not isinstance(valeur, str) or valeur.startswith(_SENTINELLE):
        return None
    try:
        return datetime.strptime(valeur[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _comptes(payload: dict[str, Any] | list[Any]) -> list[Any]:
    if isinstance(payload, list):
        return payload
    return [compte for compte in payload.values() if isinstance(compte, dict)]


def expiration_la_plus_proche(payload: dict[str, Any] | list[Any]) -> date | None:
    """La date la plus tôt parmi les comptes connectés, ou None si aucun."""
    dates = [
        trouvee
        for compte in _comptes(payload)
        if isinstance(compte, dict)
        for trouvee in (_date_expiration(_item(compte).get("authentication_expires_at")),)
        if trouvee is not None
    ]
    return min(dates) if dates else None


def _item(compte: dict[str, Any]) -> dict[str, Any]:
    item = compte.get("item")
    return item if isinstance(item, dict) else {}
