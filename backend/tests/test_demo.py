"""Teste la composition root de la démo (doc 17 semaines 0-2) — la couture
complète, pas les briques individuelles (déjà testées module par module :
fixtures en tests/ingestion/providers/, réconciliation en
tests/ingestion/test_reconciliation.py, ventilation TVA en
tests/ingestion/test_ecritures_settlement.py, catégorisation en
tests/categorize/, écriture catégorisée en tests/workflow/).
"""

from __future__ import annotations

from pathlib import Path

from axelcompta.demo import executer


def test_executer_produit_un_pdf_valide(tmp_path: Path) -> None:
    destination = tmp_path / "liasse.pdf"
    resultat = executer(destination)
    assert resultat == destination
    assert destination.read_bytes().startswith(b"%PDF-")
