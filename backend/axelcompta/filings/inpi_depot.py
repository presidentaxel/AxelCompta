"""Dossier de dépôt des comptes annuels — Guichet Unique INPI (doc 02 §6,
doc 20). Phase 1 de doc 02 §6 : génère le dossier prêt à déposer (PDF +
données structurées) ; le dépôt réel (appel API + signature qualifiée RGS,
`workflow/signature.py`) reste V1, bloqué sur ADR-004 (doc 20 §4/§5).

`construire_payload_comptes_annuels` a la même forme que le bloc
`content.comptesAnnuels` attendu par `POST /api/annual_accounts` (doc 20
§3, contrat d'interface INPI vérifié le 2026-09-11) — pas un format
inventé, prêt à être posté tel quel le jour où l'appel API réel est câblé
(reste à compléter : `personnePhysique`/`personneMorale`/`declarant`, et
`pagination` une fois le dictionnaire de données INPI dépouillé, doc 20
§6).

`PdfDepotInpiRenderer` tient lieu, pour la démo, du « document de
synthèse » que le Guichet Unique génère lui-même côté serveur après un
vrai dépôt (doc 20 §4) — impossible à appeler sans compte e-procédures,
donc simulé. Marqué FICTIF sans ambiguïté (doc 08 §5).
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from axelcompta.closing.models import LiassePivot

from .renderer import FilingRenderer

MENTION_FICTIVE = "DOCUMENT FICTIF — DÉMO AXELCOMPTA, NE PAS DÉPOSER"


def construire_payload_comptes_annuels(liasse: LiassePivot) -> dict[str, Any]:
    """Le bloc `content.comptesAnnuels` du contrat d'interface INPI (doc 20
    §3). Valeurs par défaut les plus prudentes (pas de confidentialité, pas
    de dépôt simplifié, pas de comptes consolidés) — pas un choix
    arbitraire, à reconfigurer par dossier une fois le dictionnaire de
    données INPI dépouillé (doc 20 §6)."""
    return {
        "comptesConsolides": False,
        "dateCloture": liasse.exercice_fin.isoformat() if liasse.exercice_fin else None,
        "dateDebutExerciceComptable": (
            liasse.exercice_debut.isoformat() if liasse.exercice_debut else None
        ),
        "dateFinExerciceComptable": liasse.exercice_fin.isoformat()
        if liasse.exercice_fin
        else None,
        "dispenseDepotAnnexes": False,
        "depotSimplifie": False,
        "compteBilan": {"confidentiel": False},
        "compteResultat": {"confidentiel": False},
    }


def _ligne(dessin: canvas.Canvas, x: int, y: int, libelle: str, centimes: int) -> None:
    dessin.drawString(x, y, f"{libelle} : {centimes / 100:.2f} €")


def _entete(dessin: canvas.Canvas, liasse: LiassePivot) -> None:
    dessin.setFont("Helvetica-Bold", 16)
    dessin.drawString(50, 800, "Dépôt des comptes annuels — Guichet Unique INPI")
    dessin.setFillColorRGB(0.7, 0, 0)
    dessin.setFont("Helvetica-Bold", 11)
    dessin.drawString(50, 782, MENTION_FICTIVE)
    dessin.setFillColorRGB(0, 0, 0)
    dessin.setFont("Helvetica", 9)
    dessin.drawString(
        50,
        768,
        "Tient lieu du document de synthèse généré par le Guichet Unique "
        "après un vrai dépôt (doc 20 §4) — jamais appelé ici.",
    )
    dessin.setFont("Helvetica", 11)
    dessin.drawString(50, 744, f"Dossier {liasse.dossier_id} — exercice {liasse.exercice}")


def _corps_comptable(dessin: canvas.Canvas, liasse: LiassePivot) -> int:
    y = 710
    dessin.setFont("Helvetica-Bold", 13)
    dessin.drawString(50, y, "Compte de résultat")
    dessin.setFont("Helvetica", 11)
    for libelle, cle in (
        ("Chiffre d'affaires HT", "CA_HT"),
        ("Charges", "CHARGES"),
        ("Résultat de l'exercice", "RESULTAT"),
    ):
        y -= 20
        _ligne(dessin, 60, y, libelle, liasse.cases.get(cle, 0))

    y -= 35
    dessin.setFont("Helvetica-Bold", 13)
    dessin.drawString(50, y, "Bilan")
    dessin.setFont("Helvetica", 11)
    for libelle, cle in (
        ("Actif — Trésorerie", "TRESORERIE"),
        ("Passif — Résultat", "RESULTAT"),
        ("Passif — TVA à payer", "TVA_A_PAYER"),
    ):
        y -= 20
        _ligne(dessin, 60, y, libelle, liasse.cases.get(cle, 0))
    return y


def _zone_signature(dessin: canvas.Canvas, y: int) -> None:
    y -= 50
    dessin.setFont("Helvetica-Bold", 12)
    dessin.drawString(50, y, "Zone de signature")
    dessin.rect(50, y - 90, 495, 75, stroke=1, fill=0)
    dessin.setFont("Helvetica", 9)
    dessin.drawString(60, y - 20, "En attente de signature — dépôt non finalisé.")


class PdfDepotInpiRenderer(FilingRenderer):
    def rendre(self, liasse: LiassePivot) -> bytes:
        tampon = io.BytesIO()
        dessin = canvas.Canvas(tampon, pagesize=A4)
        _entete(dessin, liasse)
        y_fin = _corps_comptable(dessin, liasse)
        _zone_signature(dessin, y_fin)
        dessin.showPage()
        dessin.save()
        return tampon.getvalue()
