"""Teste la démo multi-dossiers (doc 17 semaine 4 : « 2-3 dossiers, pas
câblé en dur sur un seul cas »). Skip gracieux si le CSV audit est absent
sur ce poste (gitignored).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from axelcompta.demo_multi_dossiers import DOSSIERS_DEMO, executer
from axelcompta.ingestion.providers.file_import import CSV_AUDIT_PAR_DEFAUT

pytestmark = pytest.mark.skipif(
    not CSV_AUDIT_PAR_DEFAUT.is_file(),
    reason="CSV audit non présent sur ce poste (gitignored, _AUDIT_DONNEES/resultats/)",
)


def test_au_moins_deux_dossiers_de_demo_doc17_semaine4() -> None:
    assert len(DOSSIERS_DEMO) >= 2


def test_executer_produit_un_rapport_et_les_fichiers_par_dossier(tmp_path: Path) -> None:
    chemin_rapport = executer(tmp_path)
    assert chemin_rapport == tmp_path / "rapport.html"
    rapport = chemin_rapport.read_text(encoding="utf-8")

    for dossier_id, _annee in DOSSIERS_DEMO:
        assert dossier_id in rapport
        dossier_sortie = tmp_path / dossier_id
        assert (dossier_sortie / "liasse.pdf").read_bytes().startswith(b"%PDF-")
        assert (dossier_sortie / "cerfa_2065.pdf").read_bytes().startswith(b"%PDF-")
        assert (
            (dossier_sortie / "journal.fec.txt")
            .read_text(encoding="utf-8")
            .startswith("JournalCode\t")
        )
        assert (dossier_sortie / "balance.csv").is_file()
