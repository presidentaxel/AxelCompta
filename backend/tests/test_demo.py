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

from axelcompta.demo import executer, executer_cerfa_2065, executer_exports_comptables


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


def test_executer_exports_comptables_produit_fec_grand_livre_et_balance(tmp_path: Path) -> None:
    chemin_fec, chemin_gl, chemin_balance = executer_exports_comptables(tmp_path)
    assert chemin_fec.read_text(encoding="utf-8").startswith("JournalCode\t")
    assert "compte,libelle_compte" in chemin_gl.read_text(encoding="utf-8")
    assert "848.00" in chemin_balance.read_text(encoding="utf-8")  # golden test doc 17 §7
