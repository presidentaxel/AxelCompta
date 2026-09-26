"""2031-SD sur le formulaire officiel : Sophie (EURL) imposée à l'IR, comme
dans la colonne `societe_ir` de la matrice."""

from __future__ import annotations

import dataclasses
import io
from datetime import date

import pytest
from pypdf import PdfReader

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId
from axelcompta.demo_chauffeurs_type import construire_ledger, parametres_cloture
from axelcompta.filings.cerfa_2031 import PdfCerfa2031Renderer
from axelcompta.filings.liasse_fiscale import PdfLiasseFiscaleRenderer
from axelcompta.ingestion.providers.chauffeurs_demo import PROFIL_SOPHIE


def _liasse_sophie_a_l_ir() -> LiassePivot:
    ledger, _ = construire_ledger(PROFIL_SOPHIE)
    parametres = dataclasses.replace(parametres_cloture(PROFIL_SOPHIE), soumis_is=False)
    return ClotureSimplifieeService(ledger).cloturer(PROFIL_SOPHIE.dossier_id, "2025", parametres)


def _pages(pdf: bytes) -> list[str]:
    return [page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages]


def test_resultat_identite_et_declarant_sur_la_2031() -> None:
    liasse = _liasse_sophie_a_l_ir()
    benefice = liasse.cases["2031.BENEFICE"] // 100

    page_1 = _pages(PdfCerfa2031Renderer(date(2026, 9, 26)).rendre(liasse))[0]

    # Même montant en ligne 1 (bénéfice), 3 (total) et 4 (bénéfice imposable).
    assert page_1.count(f"{benefice}") >= 3
    assert liasse.identite is not None
    assert liasse.identite.denomination in page_1
    assert "26/09/2026" in page_1
    assert "AxelCompta" in page_1


def test_l_associe_unique_porte_tout_le_resultat_en_2031_bis() -> None:
    liasse = _liasse_sophie_a_l_ir()
    benefice = liasse.cases["2031.BENEFICE"] // 100
    assert liasse.identite is not None
    (associe,) = liasse.identite.associes

    page_2 = _pages(PdfCerfa2031Renderer(date(2026, 9, 26)).rendre(liasse))[1]

    assert associe.nom in page_2
    assert f"{benefice}" in page_2


def test_un_deficit_passe_en_colonne_2_et_se_repartit_en_negatif() -> None:
    liasse = dataclasses.replace(
        _liasse_sophie_a_l_ir(), cases={"2031.BENEFICE": 0, "2031.DEFICIT": 1_256_00}
    )

    page_1, page_2 = _pages(PdfCerfa2031Renderer(date(2026, 9, 26)).rendre(liasse))[:2]

    assert "1 256" in page_1
    assert "-1 256" in page_2


def test_une_societe_a_l_is_ne_produit_pas_de_2031() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2025", cases={"2065": 0})
    with pytest.raises(ValueError, match="2065"):
        PdfCerfa2031Renderer().rendre(liasse)


def test_la_liasse_fiscale_a_l_ir_commence_par_la_2031_puis_la_2033() -> None:
    pages = _pages(PdfLiasseFiscaleRenderer(date(2026, 9, 26)).rendre(_liasse_sophie_a_l_ir()))

    assert "2031-SD" in pages[0]
    assert "2031 Bis-SD" in pages[1]
    assert "2033-A" in pages[2]
    assert not any("2065-SD" in page for page in pages)
