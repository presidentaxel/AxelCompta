"""Rendu CERFA 2065-SD fidèle (doc 17 §3 : « une case-clé 2065 » ; ADR-006).

Overlay sur le **vrai formulaire officiel** (`cerfa/2065-sd_2026.pdf`,
téléchargé depuis impots.gouv.fr, millésime 2026) : ce PDF n'a **aucun
champ AcroForm** — vérifié en l'inspectant (pypdf), pas supposé. C'est
exactement le chemin de repli que prévoyait l'ADR-006 : overlay de texte
aux coordonnées de la cellule, pas remplissage de champ de formulaire.

Cases remplies, toutes repérées sur les bordures de cellule réelles du PDF
(pdfplumber), pas devinées — et toutes des faits qu'on connaît vraiment,
jamais inventés (2026-09-05, suite à « il me faut tout sur le dossier ») :
- Cadre C.1 « Bénéfice imposable au taux normal » / « Déficit », depuis la
  case `"2065"` de la `LiassePivot`.
- Exercice ouvert/clos : année civile complète déduite de `liasse.exercice`
  (01/01 au 31/12) — c'est l'hypothèse déjà prise à l'ingestion (doc 17 §3,
  `demo_dossier_reel.py` filtre bien sur l'année civile).
- Cadre "Régime réel normal" : coché, seul profil du démo (doc 17 §3).
- Cadre F "Comptabilité informatisée" : OUI + logiciel "AxelCompta" — vrai
  par construction, pas une estimation.

**Ce que ce renderer NE fait PAS, volontairement** : Cadre A (désignation
de la société, SIRET, adresse) reste blanc. On ne modélise aucune identité
d'entreprise (ni pour le dossier démo synthétique, ni a fortiori pour un
vrai dossier historique, pseudonymisé exprès à l'audit, doc 07 §2.2) —
inventer un nom d'entreprise ou un SIRET pour remplir la case serait fabriquer
une donnée, pas en afficher une vraie. Idem pour les autres cases (groupes de
sociétés, plus-values, abattements, CES/CTM, rémunérations, dons...) qui ne
s'appliquent pas à notre profil démo — rester blanches est correct, pas un
manque.

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
LOGICIEL = "AxelCompta"

# Coordonnées (points PDF, origine bas-gauche), page 1, repérées via les
# bordures de cellule réelles du millésime 2026.
X_BENEFICE = 484.0
X_DEFICIT = 577.0
Y_LIGNE_RESULTAT_FISCAL = 502.5

X_EXERCICE_OUVERT, X_EXERCICE_CLOS = 138.0, 253.0
Y_LIGNE_EXERCICE = 726.29

X_REGIME_REEL_NORMAL = 563.5
Y_LIGNE_REGIME = 707.6

X_COMPTA_INFORMATISEE_OUI, X_COMPTA_INFORMATISEE_LOGICIEL = 238.0, 476.0
Y_LIGNE_COMPTA_INFORMATISEE = 150.0


def _formatter_euros(centimes: int) -> str:
    valeur = f"{abs(centimes) / 100:,.2f}"
    return valeur.replace(",", " ").replace(".", ",")


def _dessiner_resultat(dessin: canvas.Canvas, resultat_cts: int) -> None:
    dessin.setFont("Helvetica-Bold", 9)
    x = X_BENEFICE if resultat_cts >= 0 else X_DEFICIT
    dessin.drawRightString(x, Y_LIGNE_RESULTAT_FISCAL, _formatter_euros(resultat_cts))


def _dessiner_identification(dessin: canvas.Canvas, exercice: str) -> None:
    dessin.setFont("Helvetica", 9)
    dessin.drawString(X_EXERCICE_OUVERT, Y_LIGNE_EXERCICE, f"01/01/{exercice}")
    dessin.drawString(X_EXERCICE_CLOS, Y_LIGNE_EXERCICE, f"31/12/{exercice}")
    dessin.setFont("Helvetica-Bold", 9)
    dessin.drawCentredString(X_REGIME_REEL_NORMAL, Y_LIGNE_REGIME, "X")
    dessin.drawCentredString(X_COMPTA_INFORMATISEE_OUI, Y_LIGNE_COMPTA_INFORMATISEE, "X")
    dessin.setFont("Helvetica", 8)
    dessin.drawString(X_COMPTA_INFORMATISEE_LOGICIEL, Y_LIGNE_COMPTA_INFORMATISEE, LOGICIEL)


class PdfCerfa2065Renderer(FilingRenderer):
    """`liasse.cases["2065"]` : positif → case Bénéfice, négatif → case Déficit."""

    def rendre(self, liasse: LiassePivot) -> bytes:
        # clone_from attache toutes les pages au writer d'emblée : merge_page
        # sur une page déjà attachée, pas le chemin déprécié de pypdf.
        writer = PdfWriter(clone_from=CHEMIN_FORMULAIRE_OFFICIEL)
        page_1 = writer.pages[0]
        largeur, hauteur = float(page_1.mediabox.width), float(page_1.mediabox.height)

        tampon = io.BytesIO()
        dessin = canvas.Canvas(tampon, pagesize=(largeur, hauteur))
        _dessiner_resultat(dessin, liasse.cases.get("2065", 0))
        _dessiner_identification(dessin, liasse.exercice)
        dessin.save()
        tampon.seek(0)

        page_1.merge_page(PdfReader(tampon).pages[0])

        sortie = io.BytesIO()
        writer.write(sortie)
        return sortie.getvalue()
