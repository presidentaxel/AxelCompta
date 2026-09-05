from __future__ import annotations

import io

from pypdf import PdfReader

from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId
from axelcompta.filings.cerfa_2065 import PdfCerfa2065Renderer


def test_remplit_la_case_benefice_si_resultat_positif() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026", cases={"2065": 728_15})
    pdf = PdfCerfa2065Renderer().rendre(liasse)
    assert pdf.startswith(b"%PDF-")

    texte = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "728,15" in texte


def test_remplit_la_case_deficit_si_resultat_negatif() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026", cases={"2065": -50_00})
    pdf = PdfCerfa2065Renderer().rendre(liasse)
    texte = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "50,00" in texte


def test_conserve_les_5_pages_du_formulaire_officiel() -> None:
    # Formulaire (1) + annexe 2065 bis-SD (1) + notice (3) = 5 pages réelles,
    # vérifié par pypdf sur le PDF source (le `file` Unix se trompait : 3).
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026", cases={"2065": 0})
    pdf = PdfCerfa2065Renderer().rendre(liasse)
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 5
