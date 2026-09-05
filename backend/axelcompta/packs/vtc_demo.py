"""Pack VTC réduit pour la démo (doc 17 §3, §4bis).

Charge les fichiers de l'audit directement — `regles_regex.csv` (12 règles)
et `mapping_pcg_categorie.csv` — plutôt que de les dupliquer ici
(packs/README.md). Ces deux fichiers sont commités (contrairement au CSV
FEC et au modèle ML, gitignorés) : toujours présents sur un clone du repo.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from axelcompta.core.pcg import nature_depuis_compte as nature_depuis_compte

# backend/axelcompta/packs/vtc_demo.py -> racine du repo
RACINE_PACKS_VTC = Path(__file__).resolve().parents[3] / "_AUDIT_DONNEES" / "packs_vtc"
CHEMIN_REGLES_PAR_DEFAUT = RACINE_PACKS_VTC / "regles_regex.csv"
CHEMIN_MAPPING_PAR_DEFAUT = RACINE_PACKS_VTC / "mapping_pcg_categorie.csv"


@dataclass(frozen=True, slots=True)
class RegleCategorisation:
    """Une règle du pack : motif regex, catégorie, confiance (doc 05 §2)."""

    motif: re.Pattern[str]
    categorie: str
    confiance: str


def charger_regles(chemin: Path | None = None) -> tuple[RegleCategorisation, ...]:
    chemin = chemin or CHEMIN_REGLES_PAR_DEFAUT
    with chemin.open(newline="", encoding="utf-8") as fichier:
        return tuple(
            RegleCategorisation(re.compile(ligne["regex"]), ligne["categorie"], ligne["confiance"])
            for ligne in csv.DictReader(fichier)
        )


def charger_compte_par_categorie(chemin: Path | None = None) -> dict[str, str]:
    """Premier compte listé par catégorie dans le mapping — choix déterministe,
    **pas un jugement comptable validé** (le mapping est un brouillon
    d'audit, doc 12 §0.2 : « à densifier avec le comptable avant
    production »). Plusieurs comptes PCG peuvent correspondre à une même
    catégorie ; on ne tranche pas ici lequel est le bon, on prend le premier
    pour que la démo tourne.
    """
    chemin = chemin or CHEMIN_MAPPING_PAR_DEFAUT
    comptes: dict[str, str] = {}
    with chemin.open(newline="", encoding="utf-8") as fichier:
        for ligne in csv.DictReader(fichier):
            comptes.setdefault(ligne["categorie"], ligne["prefixe_compte_pcg_normalise"])
    return comptes
