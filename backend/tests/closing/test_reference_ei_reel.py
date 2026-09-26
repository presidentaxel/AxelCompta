"""Dossier de référence de la colonne « entreprise individuelle au réel »
(doc 06 §7, doc 09 §3) : le grand livre de Karim, repris comme celui d'un
exploitant en EI. L'apport initial passe au compte de l'exploitant (108)
au lieu du capital social (101) ; le reste est identique. Les chiffres
attendus sont ceux de Karim à l'IR, recalculés à la main
(`test_cloture_fiscale.py`)."""

from __future__ import annotations

import dataclasses
import io

from pypdf import PdfReader

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.models import LiassePivot
from axelcompta.demo_chauffeurs_type import construire_ledger, parametres_cloture
from axelcompta.demo_identites import IDENTITES_DEMO
from axelcompta.filings.liasse_fiscale import PdfLiasseFiscaleRenderer
from axelcompta.ingestion.providers.chauffeurs_demo import PROFIL_KARIM
from axelcompta.ledger.memory import InMemoryLedgerService

APPORT_EUROS = IDENTITES_DEMO[PROFIL_KARIM.dossier_id].capital_social_cts // 100


def _cloturer_en_ei() -> LiassePivot:
    ledger_societe, _ = construire_ledger(PROFIL_KARIM)
    ledger = InMemoryLedgerService()
    for ecriture in ledger_societe.grand_livre(PROFIL_KARIM.dossier_id):
        lignes = tuple(
            dataclasses.replace(ligne, compte="108") if ligne.compte == "101" else ligne
            for ligne in ecriture.lignes
        )
        ledger.enregistrer(dataclasses.replace(ecriture, lignes=lignes))
    identite = IDENTITES_DEMO[PROFIL_KARIM.dossier_id]
    exploitant = dataclasses.replace(identite.associes[0], qualite="Exploitant", nb_titres=0)
    identite_ei = dataclasses.replace(identite, capital_social_cts=0, associes=(exploitant,))
    parametres = dataclasses.replace(
        parametres_cloture(PROFIL_KARIM),
        forme_juridique="EI",
        identite=identite_ei,
        soumis_is=False,
        associes=False,
    )
    return ClotureSimplifieeService(ledger).cloturer(PROFIL_KARIM.dossier_id, "2025", parametres)


def _euros(liasse: LiassePivot, cle: str) -> int:
    return liasse.cases.get(cle, 0) // 100


def test_resultat_de_l_exploitant_sans_is() -> None:
    liasse = _cloturer_en_ei()
    assert _euros(liasse, "2033B.310") == 1_166
    assert _euros(liasse, "2033B.370") == _euros(liasse, "2031.BENEFICE") == 1_234
    assert not any(cle.startswith("2065.") for cle in liasse.cases)


def test_bilan_de_l_exploitant_equilibre_avec_l_apport_en_capital_individuel() -> None:
    liasse = _cloturer_en_ei()
    actif_net = _euros(liasse, "2033A.110") - _euros(liasse, "2033A.112")
    assert actif_net == _euros(liasse, "2033A.180")
    assert _euros(liasse, "2033A.120") == APPORT_EUROS  # compte de l'exploitant (108)
    assert _euros(liasse, "2033A.136") == 1_166


def test_ni_associe_ni_composition_du_capital_dans_la_liasse() -> None:
    liasse = _cloturer_en_ei()
    assert liasse.identite is not None
    exploitant = liasse.identite.dirigeant
    # Marqueurs propres aux blocs d'associés (la dénomination, elle, figure
    # en tête de chaque page) : « Prénom NOM, » au cadre E de la 2031-bis,
    # la date de naissance au 2033-F.
    ligne_cadre_e = f"{exploitant.prenoms} {exploitant.nom},"
    naissance = exploitant.date_naissance.strftime("%d/%m/%Y")

    pdf = PdfLiasseFiscaleRenderer().rendre(liasse)
    pages = [page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages]

    assert "2031-SD" in pages[0]
    assert exploitant.nom in pages[0]  # le déclarant
    assert ligne_cadre_e not in pages[1]
    page_2033f = next(page for page in pages if "2033-F" in page)
    assert naissance not in page_2033f
