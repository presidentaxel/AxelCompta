from __future__ import annotations

from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId
from axelcompta.filings.liasse_simplifiee import PdfLiasseSimplifieeRenderer

CASES = {
    "CA_HT": 945_45,
    "CHARGES": 160_00,
    "RESULTAT": 785_45,
    "TRESORERIE": 848_00,
    "TVA_A_PAYER": 62_55,
    "2065": 785_45,
}


def test_rendre_produit_des_octets_pdf_valides() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026", cases=CASES)
    pdf = PdfLiasseSimplifieeRenderer().rendre(liasse)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 100
