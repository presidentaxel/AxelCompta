"""Sérialisation JSON de `IdentiteEntreprise` pour la colonne
`dossiers.identite` (Postgres). Dates en ISO 8601, montants en centimes."""

from __future__ import annotations

import dataclasses
from datetime import date
from typing import Any

from axelcompta.core.identite import Adresse, Associe, IdentiteEntreprise


def identite_vers_json(identite: IdentiteEntreprise | None) -> dict[str, Any] | None:
    if identite is None:
        return None
    donnees = dataclasses.asdict(identite)
    for associe in donnees["associes"]:
        associe["date_naissance"] = associe["date_naissance"].isoformat()
    return donnees


def _associe(donnees: dict[str, Any]) -> Associe:
    return Associe(
        **{
            **donnees,
            "date_naissance": date.fromisoformat(donnees["date_naissance"]),
            "adresse": Adresse(**donnees["adresse"]),
        }
    )


def identite_depuis_json(donnees: dict[str, Any] | None) -> IdentiteEntreprise | None:
    if donnees is None:
        return None
    return IdentiteEntreprise(
        **{
            **donnees,
            "adresse_siege": Adresse(**donnees["adresse_siege"]),
            "associes": tuple(_associe(a) for a in donnees["associes"]),
        }
    )
