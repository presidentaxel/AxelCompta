"""Rendu PDF « Hello World » (doc 17 semaine 0) : liste brute des soldes par
compte d'une LiassePivot. Aucune mise en forme réglementaire — ça viendra en
semaine 3 (doc 06 §6), avec conformité CERFA explicitement hors scope démo
(doc 17 §3). Sert juste à prouver que la couture clôture → PDF existe.
"""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from axelcompta.closing.models import LiassePivot

from .renderer import FilingRenderer


class PdfBouchonRenderer(FilingRenderer):
    def rendre(self, liasse: LiassePivot) -> bytes:
        tampon = io.BytesIO()
        dessin = canvas.Canvas(tampon, pagesize=A4)
        dessin.setFont("Helvetica-Bold", 16)
        dessin.drawString(50, 800, "AxeLCompta — Liasse (démo, doc 17 semaine 0)")
        dessin.setFont("Helvetica", 11)
        dessin.drawString(50, 770, f"Dossier {liasse.dossier_id} — exercice {liasse.exercice}")
        position_y = 730
        for compte, centimes in sorted(liasse.cases.items()):
            dessin.drawString(60, position_y, f"{compte} : {centimes / 100:.2f} €")
            position_y -= 20
        dessin.showPage()
        dessin.save()
        return tampon.getvalue()
