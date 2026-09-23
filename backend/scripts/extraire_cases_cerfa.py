"""Repère les cases numérotées d'un formulaire CERFA sans AcroForm (ADR-006)
et écrit leurs coordonnées dans un JSON versionné à côté du PDF.

Principe : chaque code de case (« 084 », « 310 »...) est imprimé dans une
petite cellule bordée ; la zone de saisie est la cellule suivante à droite.
On lit les bordures réelles du PDF (pdfplumber), rien n'est deviné. Un
nombre à trois chiffres qui n'est pas encadré serré (« art. 302 septies »)
n'est pas un code de case et est écarté.

À relancer à chaque nouveau millésime, puis vérifier le rendu à l'œil :
un overlay mal aligné ne lève aucune erreur (ADR-006).

Usage, depuis backend/ (pdfplumber : `pip install -e ".[dev]"`) :

    python scripts/extraire_cases_cerfa.py \\
        axelcompta/filings/cerfa/2033-sd_2026.pdf \\
        axelcompta/filings/cerfa/cases_2033-sd_2026.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pdfplumber

# Codes imprimés en dessin vectoriel (pas en texte) sur le millésime 2026 :
# page → code → (code de la même colonne, code de la même ligne).
DEDUITS = {"3": {"460": ("450", "462")}}
MARGE_CADRE = 10.5  # écart max (pt) entre le code et les bords de sa cellule
LARGEUR_MIN_CELLULE = 2.0


def _bords_verticaux(page: Any, y_milieu: float) -> list[float]:
    return sorted(
        {
            round(float(e["x0"]), 1)
            for e in page.edges
            if e["orientation"] == "v" and e["top"] - 1 <= y_milieu <= e["bottom"] + 1
        }
    )


def _case(page: Any, mot: dict[str, Any]) -> list[float] | None:
    """[x_gauche, x_droite, y_ligne_de_base] de la zone de saisie, ou None."""
    bords = _bords_verticaux(page, (mot["top"] + mot["bottom"]) / 2)
    gauche = [x for x in bords if x <= mot["x0"] + 0.5]
    droite = [x for x in bords if x >= mot["x1"] - 0.5]
    if not gauche or not droite:
        return None
    if mot["x0"] - gauche[-1] > MARGE_CADRE or droite[0] - mot["x1"] > MARGE_CADRE:
        return None
    suivants = [x for x in droite[1:] if x - droite[0] > LARGEUR_MIN_CELLULE]
    if not suivants:
        return None
    hauteur = float(page.height)
    return [droite[0], suivants[0], round(hauteur - float(mot["bottom"]), 1)]


def extraire(chemin_pdf: Path) -> dict[str, dict[str, list[float]]]:
    resultat: dict[str, dict[str, list[float]]] = {}
    with pdfplumber.open(chemin_pdf) as pdf:
        for numero, page in enumerate(pdf.pages, start=1):
            cases: dict[str, list[float]] = {}
            for mot in page.extract_words():
                if not re.fullmatch(r"\d{3}", mot["text"]) or mot["text"] in cases:
                    continue
                case = _case(page, mot)
                if case is not None:
                    cases[mot["text"]] = case
            resultat[str(numero)] = cases
    for page, deduits in DEDUITS.items():
        for code, (meme_colonne, meme_ligne) in deduits.items():
            x_gauche, x_droite, _ = resultat[page][meme_colonne]
            resultat[page][code] = [x_gauche, x_droite, resultat[page][meme_ligne][2]]
    return resultat


def main() -> int:
    source, cible = Path(sys.argv[1]), Path(sys.argv[2])
    cases = extraire(source)
    cible.write_text(json.dumps(cases, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for page, codes in cases.items():
        print(f"page {page} : {len(codes)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
