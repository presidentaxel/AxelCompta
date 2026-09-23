from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId
from axelcompta.demo_chauffeurs_type import construire_ledger, parametres_cloture
from axelcompta.filings.cerfa_2033 import PAGES, PdfLiasse2033Renderer, charger_cases
from axelcompta.ingestion.providers.chauffeurs_demo import PROFIL_KARIM


def _liasse_karim() -> LiassePivot:
    ledger, _ = construire_ledger(PROFIL_KARIM)
    service = ClotureSimplifieeService(ledger)
    return service.cloturer(PROFIL_KARIM.dossier_id, "2025", parametres_cloture(PROFIL_KARIM))


def _pages() -> list[str]:
    pdf = PdfLiasse2033Renderer().rendre(_liasse_karim())
    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages]


def test_toutes_les_cases_calculees_existent_sur_le_formulaire() -> None:
    # Une case calculée sans coordonnée serait silencieusement absente du PDF.
    cases = charger_cases()
    liasse = _liasse_karim()
    for cle in liasse.cases:
        tableau, _, code = cle.partition(".")
        if tableau in PAGES and "." not in code and code != "ECART_ARRONDI":
            assert code in cases[str(PAGES[tableau])], cle


def test_sept_tableaux_remplis() -> None:
    pages = _pages()
    assert len(pages) == 7
    bilan, resultat = pages[0], pages[1]
    assert "AMRANI VTC" in bilan and "14 rue de la Fontaine au Roi" in bilan
    assert "3 074" in bilan and "1 000" in bilan  # total bilan, capital
    assert "14 191" in resultat and "1 234" in resultat  # CA, résultat fiscal


def test_capital_et_associe_du_2033f() -> None:
    capital = _pages()[5]
    for attendu in ("AMRANI", "Karim", "100,00", "14/03/1988", "Saint-Denis"):
        assert attendu in capital


def test_refuse_une_liasse_sans_cloture_fiscale() -> None:
    with pytest.raises(ValueError):
        PdfLiasse2033Renderer().rendre(LiassePivot(DossierId("d"), "2025", {"2065": 0}))
