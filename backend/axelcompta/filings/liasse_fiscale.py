"""Liasse fiscale complète au régime simplifié, en un seul PDF, dans l'ordre
de dépôt : la déclaration de résultat (2065-SD et 2065-bis-SD à l'IS,
2031-SD et 2031-bis-SD à l'IR, selon `liasse.soumis_is`), puis 2033-A à G.

Les pages de notice des formulaires officiels ne sont pas reprises : ce
document se relit et se signe, il ne s'imprime pas pour être rempli.
"""

from __future__ import annotations

import io
from datetime import date

from pypdf import PdfReader, PdfWriter

from axelcompta.closing.models import LiassePivot

from .cerfa_2031 import PAGES_REMPLIES as PAGES_2031_REMPLIES
from .cerfa_2031 import PdfCerfa2031Renderer
from .cerfa_2033 import PdfLiasse2033Renderer
from .cerfa_2065 import PdfCerfa2065Renderer
from .renderer import FilingRenderer

PAGES_2065_REMPLIES = 2  # 2065-SD + 2065-bis-SD ; les 3 suivantes sont la notice


class PdfLiasseFiscaleRenderer(FilingRenderer):
    def __init__(self, date_etablissement: date | None = None) -> None:
        self._date = date_etablissement

    def rendre(self, liasse: LiassePivot) -> bytes:
        if liasse.soumis_is:
            pdf, pages = PdfCerfa2065Renderer(self._date).rendre(liasse), PAGES_2065_REMPLIES
        else:
            pdf, pages = PdfCerfa2031Renderer(self._date).rendre(liasse), PAGES_2031_REMPLIES
        declaration = PdfReader(io.BytesIO(pdf))
        tableaux = PdfReader(io.BytesIO(PdfLiasse2033Renderer().rendre(liasse)))
        sortie = PdfWriter()
        for page in declaration.pages[:pages]:
            sortie.add_page(page)
        for page in tableaux.pages:
            sortie.add_page(page)
        tampon = io.BytesIO()
        sortie.write(tampon)
        return tampon.getvalue()
