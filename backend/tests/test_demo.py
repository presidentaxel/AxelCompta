"""Teste la composition root de la démo (doc 17 semaines 0-3) — la couture
complète, pas les briques individuelles (déjà testées module par module :
fixtures en tests/ingestion/providers/, réconciliation en
tests/ingestion/test_reconciliation.py, ventilation TVA en
tests/ingestion/test_ecritures_settlement.py, catégorisation en
tests/categorize/, écriture catégorisée en tests/workflow/, clôture en
tests/closing/, rendus en tests/filings/).
"""

from __future__ import annotations

from pathlib import Path

from axelcompta.demo import executer, executer_cerfa_2065


def test_executer_produit_la_liasse_simplifiee(tmp_path: Path) -> None:
    destination = tmp_path / "liasse.pdf"
    resultat = executer(destination)
    assert resultat == destination
    assert destination.read_bytes().startswith(b"%PDF-")


def test_executer_cerfa_2065_produit_le_formulaire_officiel_rempli(tmp_path: Path) -> None:
    destination = tmp_path / "cerfa.pdf"
    resultat = executer_cerfa_2065(destination)
    assert resultat == destination
    assert destination.read_bytes().startswith(b"%PDF-")
