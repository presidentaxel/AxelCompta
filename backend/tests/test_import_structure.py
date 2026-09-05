"""Vérifie que le squelette de modules s'importe sans erreur.

Pas un test métier (il n'y a pas encore de logique métier à tester) — juste
la garantie que l'arborescence de doc 03 §3 est un package Python cohérent.
"""

from __future__ import annotations

import importlib

MODULES = [
    "axelcompta",
    "axelcompta.core",
    "axelcompta.core.money",
    "axelcompta.core.ids",
    "axelcompta.core.errors",
    "axelcompta.tenants",
    "axelcompta.tenants.models",
    "axelcompta.packs",
    "axelcompta.packs.models",
    "axelcompta.ingestion",
    "axelcompta.ingestion.providers",
    "axelcompta.ingestion.providers.base",
    "axelcompta.ingestion.providers.digifactory",
    "axelcompta.ingestion.providers.rollee",
    "axelcompta.ingestion.providers.file_import",
    "axelcompta.ingestion.providers.fixture",
    "axelcompta.documents",
    "axelcompta.categorize",
    "axelcompta.categorize.models",
    "axelcompta.categorize.pipeline",
    "axelcompta.anomaly",
    "axelcompta.ledger",
    "axelcompta.ledger.models",
    "axelcompta.ledger.service",
    "axelcompta.closing",
    "axelcompta.closing.models",
    "axelcompta.closing.service",
    "axelcompta.filings",
    "axelcompta.filings.renderer",
    "axelcompta.workflow",
    "axelcompta.api",
    "axelcompta.api.app",
    "axelcompta.ml",
]


def test_tous_les_modules_simportent() -> None:
    for nom in MODULES:
        importlib.import_module(nom)
