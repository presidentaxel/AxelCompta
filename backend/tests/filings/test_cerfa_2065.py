from __future__ import annotations

import io
from datetime import date

from pypdf import PdfReader

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId
from axelcompta.demo_chauffeurs_type import construire_ledger, parametres_cloture
from axelcompta.filings.cerfa_2065 import PdfCerfa2065Renderer
from axelcompta.ingestion.providers.chauffeurs_demo import PROFIL_SOPHIE


def test_remplit_la_case_benefice_si_resultat_positif() -> None:
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2026", cases={"2065": 728_15})
    pdf = PdfCerfa2065Renderer().rendre(liasse)
    assert pdf.startswith(b"%PDF-")

    texte = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "728,15" in texte


def test_remplit_exercice_regime_et_comptabilite_informatisee() -> None:
    # Liasse sans identité (dossier historique pseudonymisé) : l'identité
    # reste blanche, on n'en invente pas.
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2024", cases={"2065": 0})
    pdf = PdfCerfa2065Renderer().rendre(liasse)
    texte = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "01/01/2024" in texte
    assert "31/12/2024" in texte
    assert "AxelCompta" in texte


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


def _pages_sophie() -> list[str]:
    ledger, _ = construire_ledger(PROFIL_SOPHIE)
    liasse = ClotureSimplifieeService(ledger).cloturer(
        PROFIL_SOPHIE.dossier_id, "2025", parametres_cloture(PROFIL_SOPHIE)
    )
    pdf = PdfCerfa2065Renderer(date(2026, 9, 23)).rendre(liasse)
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]


def test_cloture_fiscale_remplit_identite_activite_et_signataire() -> None:
    declaration = _pages_sophie()[0]
    for attendu in (
        "SM CHAUFFEUR PRIVE",
        "6 avenue Jean Jaurès, 92120 Montrouge",
        "sophie@sm-chauffeur.example.com",
        "Transport de personnes par VTC (APE 4932Z)",
        "06/01/2025",
        "31/12/2025",
        "Gérante, Sophie MARCHAND",
        "23/09/2026",
    ):
        assert attendu in declaration, attendu


def test_cloture_fiscale_benefice_au_taux_reduit_sans_centimes() -> None:
    declaration = _pages_sophie()[0]
    assert "736" in declaration  # 581 + 110 (IS) + 45 (amende) : base à 15 %
    assert "736,00" not in declaration


def test_cloture_fiscale_remplit_le_cadre_j_de_l_annexe() -> None:
    cases = {"2065": 0, "2065.IMPOT": 0, "2033B.310": 0, "2065J.SALAIRES": 12_345_00}
    liasse = LiassePivot(dossier_id=DossierId("d1"), exercice="2025", cases=cases)
    annexe = PdfReader(io.BytesIO(PdfCerfa2065Renderer().rendre(liasse))).pages[1]
    assert "12 345" in (annexe.extract_text() or "")
