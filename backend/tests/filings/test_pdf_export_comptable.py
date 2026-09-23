from __future__ import annotations

import io
from datetime import date, timedelta

from pypdf import PdfReader

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.filings.pdf_export_comptable import (
    _id_ecriture_affiche,
    rendre_balance_pdf,
    rendre_grand_livre_pdf,
)
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

DOSSIER = DossierId("DEMO_karim")


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


def _pages(pdf: bytes) -> list[str]:
    lecteur = PdfReader(io.BytesIO(pdf))
    return [page.extract_text() or "" for page in lecteur.pages]


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


def test_id_ecriture_affiche_garde_la_fin_discriminante() -> None:
    assert _id_ecriture_affiche("DEMO_karim:settlement-1") == "DEMO_karim:settlement-1"
    long_id = "DEMO_portefeuille_tres_long:settlement-12"
    affiche = _id_ecriture_affiche(long_id)
    assert affiche.endswith("settlement-12")
    assert affiche.startswith("…")
    assert "portefeuille_tres_long" not in affiche


def test_grand_livre_pdf_distingue_deux_settlements() -> None:
    """Bugbot : tronquer à 18 chars au début rendait tous les DEMO_*:settlement
    identiques."""
    ecritures = (
        Ecriture(
            id=EcritureId("DEMO_karim:settlement-1"),
            dossier_id=DOSSIER,
            journal=Journal.BQ,
            date=date(2026, 1, 1),
            libelle="Settlement 1",
            reference_piece=None,
            lignes=(
                LigneEcriture("512", Sens.DEBIT, Money(100_00)),
                LigneEcriture("706", Sens.CREDIT, Money(100_00)),
            ),
        ),
        Ecriture(
            id=EcritureId("DEMO_karim:settlement-2"),
            dossier_id=DOSSIER,
            journal=Journal.BQ,
            date=date(2026, 1, 2),
            libelle="Settlement 2",
            reference_piece=None,
            lignes=(
                LigneEcriture("512", Sens.DEBIT, Money(200_00)),
                LigneEcriture("706", Sens.CREDIT, Money(200_00)),
            ),
        ),
    )
    texte = _texte_pdf(rendre_grand_livre_pdf(ecritures, dossier_id=str(DOSSIER)))
    assert "settlement-1" in texte
    assert "settlement-2" in texte


def test_grand_livre_pdf_repete_entete_compte_apres_saut_de_page() -> None:
    """Bugbot : un saut de page au milieu d'un compte doit redessiner
    l'en-tête de compte + colonnes, pas seulement le titre du document."""
    ecritures: list[Ecriture] = []
    for i in range(80):
        ecritures.append(
            Ecriture(
                id=EcritureId(f"DEMO_karim:categorise-{i}"),
                dossier_id=DOSSIER,
                journal=Journal.BQ,
                date=date(2026, 1, 1) + timedelta(days=i % 28),
                libelle=f"Mouvement {i}",
                reference_piece=None,
                lignes=(
                    LigneEcriture("512", Sens.DEBIT, Money(10_00)),
                    LigneEcriture("606", Sens.CREDIT, Money(10_00)),
                ),
            )
        )
    pages = _pages(rendre_grand_livre_pdf(tuple(ecritures), dossier_id=str(DOSSIER)))
    assert len(pages) >= 2
    pages_512 = [page for page in pages if "Compte 512" in page]
    # Au moins 2 pages portent l'en-tête 512 → redessiné après saut de page.
    assert len(pages_512) >= 2
    for page in pages:
        assert "Compte 512" in page or "Compte 606" in page
        assert "Débit" in page
        assert "Crédit" in page
