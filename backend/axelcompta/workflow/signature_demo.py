"""SignatureDemoProvider — chemin B (doc 16 §7 : même idiome que
DigifactoryProvider avant le déblocage) : tamponne un PDF pour montrer le
parcours de signature en démo, sans jamais produire une vraie signature
électronique qualifiée RGS (doc 20 §4 — impossible sans certificat +
prestataire réel, ADR-004 toujours en devis).

Le tampon appliqué (rouge, en travers de la page) reste lisible même si un
document généré par ce provider fuitait hors de la démo par erreur — c'est
le but (doc 08 §5, doctrine d'erreurs).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from axelcompta.core.ids import UserId

from .signature import DocumentSigne, SignatureProvider

MENTION_FICTIVE = "SIGNÉ — DÉMO AXELCOMPTA, DOCUMENT FICTIF, NE PAS DÉPOSER"


def _tampon(largeur: float, hauteur: float, signataire: str, signe_le: datetime) -> bytes:
    tampon = io.BytesIO()
    dessin = canvas.Canvas(tampon, pagesize=(largeur, hauteur))
    dessin.saveState()
    dessin.translate(largeur / 2, hauteur / 2)
    dessin.rotate(30)
    dessin.setFillColorRGB(0.75, 0, 0)
    dessin.setFont("Helvetica-Bold", 15)
    dessin.drawCentredString(0, 0, MENTION_FICTIVE)
    dessin.restoreState()
    dessin.setFillColorRGB(0.75, 0, 0)
    dessin.setFont("Helvetica", 9)
    dessin.drawString(
        50, 30, f"Signé (démo) par {signataire} le {signe_le.strftime('%d/%m/%Y %H:%M')} UTC"
    )
    dessin.save()
    tampon.seek(0)
    return tampon.getvalue()


class SignatureDemoProvider(SignatureProvider):
    def signer(self, contenu_pdf: bytes, signataire: UserId) -> DocumentSigne:
        signe_le = datetime.now(UTC)
        lecteur_source = PdfReader(io.BytesIO(contenu_pdf))
        page_1 = lecteur_source.pages[0]
        largeur, hauteur = float(page_1.mediabox.width), float(page_1.mediabox.height)

        overlay = PdfReader(io.BytesIO(_tampon(largeur, hauteur, signataire, signe_le)))
        writer = PdfWriter(clone_from=lecteur_source)
        writer.pages[0].merge_page(overlay.pages[0])

        sortie = io.BytesIO()
        writer.write(sortie)
        return DocumentSigne(
            contenu_pdf=sortie.getvalue(),
            signataire=signataire,
            signe_le=signe_le,
            provider="demo",
            qualifie=False,
        )
