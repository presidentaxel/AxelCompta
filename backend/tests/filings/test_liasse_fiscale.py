from __future__ import annotations

import io
from datetime import date

from pypdf import PdfReader

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.demo_chauffeurs_type import construire_ledger, parametres_cloture
from axelcompta.filings.liasse_fiscale import PdfLiasseFiscaleRenderer
from axelcompta.ingestion.providers.chauffeurs_demo import PROFIL_YANIS


def test_2065_2065bis_puis_2033_a_g_sans_les_notices() -> None:
    ledger, _ = construire_ledger(PROFIL_YANIS)
    liasse = ClotureSimplifieeService(ledger).cloturer(
        PROFIL_YANIS.dossier_id, "2025", parametres_cloture(PROFIL_YANIS)
    )
    pdf = PdfLiasseFiscaleRenderer(date(2026, 9, 23)).rendre(liasse)
    pages = [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]
    assert len(pages) == 2 + 7
    assert "YH TRANSPORT" in pages[0] and "1 256" in pages[0]  # déficit fiscal au 2065
    assert "23/09/2026" in pages[0]
    assert "BILAN SIMPLIFIÉ" in pages[2]
