from __future__ import annotations

import io
from datetime import date

from pypdf import PdfReader

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.filings.pdf_export_comptable import rendre_balance_pdf, rendre_grand_livre_pdf
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

DOSSIER = DossierId("d1")


def _ecriture_uber() -> Ecriture:
    return Ecriture(
        id=EcritureId("e1"),
        dossier_id=DOSSIER,
        journal=Journal.BQ,
        date=date(2026, 9, 3),
        libelle="Règlement Uber",
        reference_piece=None,
        lignes=(
            LigneEcriture("512", Sens.DEBIT, Money(848_00)),
            LigneEcriture("706", Sens.CREDIT, Money(945_45)),
            LigneEcriture("44571", Sens.CREDIT, Money(94_55)),
            LigneEcriture("622", Sens.DEBIT, Money(160_00)),
            LigneEcriture("44566", Sens.DEBIT, Money(32_00)),
        ),
    )


def _texte_pdf(pdf: bytes) -> str:
    lecteur = PdfReader(io.BytesIO(pdf))
    return "\n".join(page.extract_text() or "" for page in lecteur.pages)


def test_grand_livre_pdf_contient_comptes_et_montants() -> None:
    pdf = rendre_grand_livre_pdf((_ecriture_uber(),), dossier_id=str(DOSSIER))
    assert pdf.startswith(b"%PDF")
    texte = _texte_pdf(pdf)
    assert "Grand livre" in texte
    assert "512" in texte
    assert "Banques" in texte
    assert "848.00" in texte
    assert "Règlement Uber" in texte


def test_balance_pdf_contient_totaux_equilibres() -> None:
    pdf = rendre_balance_pdf((_ecriture_uber(),), dossier_id=str(DOSSIER))
    assert pdf.startswith(b"%PDF")
    texte = _texte_pdf(pdf)
    assert "Balance" in texte
    assert "TOTAL" in texte
    # Σ débits = Σ crédits = 848+160+32 = 1040.00 et 945.45+94.55 = 1040.00
    assert "1040.00" in texte
    assert "706" in texte


def test_grand_livre_pdf_vide_reste_valide() -> None:
    pdf = rendre_grand_livre_pdf((), dossier_id="vide")
    assert pdf.startswith(b"%PDF")
    assert "Aucune écriture" in _texte_pdf(pdf)
