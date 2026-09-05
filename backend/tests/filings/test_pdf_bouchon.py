from __future__ import annotations

from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId
from axelcompta.filings.pdf_bouchon import PdfBouchonRenderer


def test_rendre_produit_des_octets_pdf_valides() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026", cases={"512": 848_00})
    pdf = PdfBouchonRenderer().rendre(liasse)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 100
