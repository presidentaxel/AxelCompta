"""Rendu CERFA 2065-SD fidèle (doc 17 §3 : « une case-clé 2065 » ; ADR-006).

Overlay sur le **vrai formulaire officiel** (`cerfa/2065-sd_2026.pdf`,
téléchargé depuis impots.gouv.fr, millésime 2026) : ce PDF n'a **aucun
champ AcroForm** — vérifié en l'inspectant (pypdf), pas supposé. C'est
exactement le chemin de repli que prévoyait l'ADR-006 : overlay de texte
aux coordonnées de la cellule, pas remplissage de champ de formulaire.

Une seule case est remplie : Cadre C.1 « Bénéfice imposable au taux
normal » (ou « Déficit » selon le signe), à partir de la case `"2065"` de
la `LiassePivot`. Les coordonnées ont été repérées sur les bordures de
cellule réelles du PDF (pdfplumber), pas devinées.

**Ce que ce renderer ne fait PAS** : remplir les autres cases (groupes de
sociétés, plus-values, abattements, CES/CTM, rémunérations, dons...) —
elles ne s'appliquent pas à notre profil démo (SASU seule, pas de groupe,
pas de plus-value), rester blanches est donc correct, pas un manque.

**Ce que ça ne prouve toujours pas** : la conformité légale réelle. Le
dépôt du 2065 est obligatoirement télétransmis par EDI/EFI (doc 02, statut
Partenaire EDI) — jamais déposé en PDF. Ce renderer produit un PDF fidèle
pour la relecture humaine, pas une télédéclaration.
"""

from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from axelcompta.closing.models import LiassePivot

from .renderer import FilingRenderer

CHEMIN_FORMULAIRE_OFFICIEL = Path(__file__).resolve().parent / "cerfa" / "2065-sd_2026.pdf"

# Coordonnées (points PDF, origine bas-gauche), page 1, Cadre C.1 :
# repérées via les bordures de cellule réelles du millésime 2026.
X_BENEFICE = 484.0
X_DEFICIT = 577.0
Y_LIGNE_RESULTAT_FISCAL = 502.5


def _formatter_euros(centimes: int) -> str:
    valeur = f"{abs(centimes) / 100:,.2f}"
    return valeur.replace(",", " ").replace(".", ",")


class PdfCerfa2065Renderer(FilingRenderer):
    """`liasse.cases["2065"]` : positif → case Bénéfice, négatif → case Déficit."""

    def rendre(self, liasse: LiassePivot) -> bytes:
        resultat_cts = liasse.cases.get("2065", 0)
        # clone_from attache toutes les pages au writer d'emblée : merge_page
        # sur une page déjà attachée, pas le chemin déprécié de pypdf.
        writer = PdfWriter(clone_from=CHEMIN_FORMULAIRE_OFFICIEL)
        page_1 = writer.pages[0]
        largeur, hauteur = float(page_1.mediabox.width), float(page_1.mediabox.height)

        tampon = io.BytesIO()
        dessin = canvas.Canvas(tampon, pagesize=(largeur, hauteur))
        dessin.setFont("Helvetica-Bold", 9)
        x = X_BENEFICE if resultat_cts >= 0 else X_DEFICIT
        dessin.drawRightString(x, Y_LIGNE_RESULTAT_FISCAL, _formatter_euros(resultat_cts))
        dessin.save()
        tampon.seek(0)

        page_1.merge_page(PdfReader(tampon).pages[0])

        sortie = io.BytesIO()
        writer.write(sortie)
        return sortie.getvalue()
