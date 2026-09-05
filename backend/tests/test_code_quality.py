"""Fait respecter deux règles du doc 08 qui n'ont pas d'équivalent natif dans
ruff/mypy/import-linter : la longueur maximale d'une fonction (doc 08 §1,
règle 4) et le fait que chaque module ait ses tests (doc 08 §3). Ce fichier
tourne à chaque `pytest` (doc 08 §4 étape 5) — donc à chaque CI.
"""

from __future__ import annotations

import ast
from pathlib import Path

MAX_FUNCTION_LINES = 60  # doc 08 §1, règle 4 : « Fonctions ≤ 60 lignes »

BACKEND = Path(__file__).resolve().parent.parent
AXELCOMPTA = BACKEND / "axelcompta"
TESTS = BACKEND / "tests"


def _fonctions_trop_longues(fichier: Path) -> list[str]:
    arbre = ast.parse(fichier.read_text(encoding="utf-8"), filename=str(fichier))
    violations = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef | ast.AsyncFunctionDef):
            fin = noeud.end_lineno or noeud.lineno
            longueur = fin - noeud.lineno + 1
            if longueur > MAX_FUNCTION_LINES:
                violations.append(
                    f"{fichier.relative_to(BACKEND)}:{noeud.lineno} — {noeud.name} "
                    f"fait {longueur} lignes (max {MAX_FUNCTION_LINES})"
                )
    return violations


def verifier_longueur_fonctions(*racines: Path) -> list[str]:
    violations: list[str] = []
    for racine in racines:
        for fichier in sorted(racine.rglob("*.py")):
            violations.extend(_fonctions_trop_longues(fichier))
    return violations


def _packages(racine: Path) -> list[Path]:
    """Tous les dossiers qui sont des packages Python (contiennent __init__.py)."""
    return sorted({chemin.parent for chemin in racine.rglob("__init__.py")})


def _modules_autonomes(racine: Path) -> list[Path]:
    """Fichiers .py directement à la racine du package, hors __init__.py — ex.
    demo.py (composition root, pas un des 14 modules d'architecture)."""
    return sorted(fichier for fichier in racine.glob("*.py") if fichier.name != "__init__.py")


def verifier_module_a_ses_tests(axelcompta: Path, tests: Path) -> list[str]:
    """Chaque package de axelcompta/ doit avoir un dossier miroir sous tests/
    avec au moins un fichier test_*.py ; chaque module autonome (ex. demo.py)
    doit avoir un tests/test_<nom>.py (doc 08 §3)."""
    violations = []
    for paquet in _packages(axelcompta):
        relatif = paquet.relative_to(axelcompta)
        dossier_tests = tests if str(relatif) == "." else tests / relatif
        if not dossier_tests.is_dir() or not any(dossier_tests.glob("test_*.py")):
            violations.append(
                f"axelcompta/{relatif} n'a pas de tests dans tests/{relatif} (doc 08 §3)"
            )
    for module in _modules_autonomes(axelcompta):
        if not (tests / f"test_{module.stem}.py").is_file():
            violations.append(
                f"axelcompta/{module.name} n'a pas de tests/test_{module.stem}.py (doc 08 §3)"
            )
    return violations


def test_aucune_fonction_ne_depasse_60_lignes() -> None:
    violations = verifier_longueur_fonctions(AXELCOMPTA, TESTS)
    assert not violations, "\n" + "\n".join(violations)


def test_chaque_module_a_ses_tests() -> None:
    violations = verifier_module_a_ses_tests(AXELCOMPTA, TESTS)
    assert not violations, "\n" + "\n".join(violations)
