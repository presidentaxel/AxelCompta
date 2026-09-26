"""Liasse 2033-A à 2033-G (régime simplifié d'imposition) sur le **vrai
formulaire officiel** (`cerfa/2033-sd_2026.pdf`, impots.gouv.fr, millésime
2026, sans champs AcroForm : overlay, ADR-006).

Toutes les cases numérotées viennent de `cerfa/cases_2033-sd_2026.json`,
généré depuis les bordures réelles du PDF par
`scripts/extraire_cases_cerfa.py` ; seuls les en-têtes (désignation,
dates, SIREN, cases « Néant ») sont positionnés ici.

Règle de remplissage, celle d'une liasse déposée : une rubrique à zéro
reste blanche, les totaux et les résultats sont toujours écrits, et un
tableau entièrement vide est coché « Néant ».

Ce PDF sert à la relecture et à la signature : le dépôt légal de la
liasse est dématérialisé (EDI-TDFC ou EFI), jamais un PDF (doc 02).
"""

from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from axelcompta.closing.models import LiassePivot
from axelcompta.core.identite import IdentiteEntreprise

from .overlay_cerfa import Cellule, OverlayCerfa
from .renderer import FilingRenderer

DOSSIER_CERFA = Path(__file__).resolve().parent / "cerfa"
CHEMIN_FORMULAIRE_2033 = DOSSIER_CERFA / "2033-sd_2026.pdf"
CHEMIN_CASES_2033 = DOSSIER_CERFA / "cases_2033-sd_2026.json"

PAGES = {"2033A": 1, "2033B": 2, "2033C": 3, "2033D": 4, "2033E": 5, "2033F": 6, "2033G": 7}
X_DROITE_NET_ACTIF = 568.1  # bord droit de la colonne 3 « Net » du 2033-A

TOTAUX: dict[str, tuple[str, ...]] = {
    "2033A": ("044", "048", "096", "098", "110", "112", "136", "142", "176", "180"),
    "2033B": ("232", "264", "270", "310"),
    "2033E": ("376", "106", "144", "152", "137", "117"),
}
# Paires bénéfice/déficit : l'une des deux est toujours écrite, même à 0.
ALTERNATIVES_2033B = (("312", "314"), ("352", "354"), ("370", "372"))

# Case « Néant » de chaque page : (x centre, y ligne de base du glyphe ☐).
NEANT: dict[str, tuple[float, float]] = {
    "2033A": (549.9, 743.6),
    "2033B": (489.4, 784.5),
    "2033C": (541.6, 775.0),
    "2033D": (500.7, 759.3),
    "2033E": (547.0, 768.9),
    "2033F": (532.2, 760.5),
    "2033G": (545.2, 759.0),
}
TAILLE_CROIX_NEANT = 6.5  # le glyphe ☐ fait ~7 pt de côté
# Désignation de l'entreprise, pages A à E : (x, y).
DESIGNATION: dict[str, tuple[float, float]] = {
    "2033A": (134.0, 743.0),
    "2033B": (300.0, 783.5),
    "2033C": (331.0, 775.5),
    "2033D": (307.0, 763.0),
    "2033E": (326.0, 767.0),
}
# « Exercice N clos le » en glyphes ☐ : (x premier jour, x premier mois,
# x première année, largeur d'une case, y).
CLOS_LE_GLYPHES = {
    "2033A": (482.1, 501.6, 521.1, 7.8, 656.0),
    "2033B": (445.7, 461.0, 476.3, 6.1, 764.3),
}


def charger_cases() -> dict[str, dict[str, Cellule]]:
    brut = json.loads(CHEMIN_CASES_2033.read_text(encoding="utf-8"))
    return {
        page: {code: (c[0], c[1], c[2]) for code, c in codes.items()}
        for page, codes in brut.items()
    }


def _euros(liasse: LiassePivot, tableau: str) -> dict[str, int]:
    prefixe = f"{tableau}."
    return {
        cle[len(prefixe) :]: centimes // 100
        for cle, centimes in liasse.cases.items()
        if cle.startswith(prefixe) and "." not in cle[len(prefixe) :]
    }


def extraire_page_2033(liasse: LiassePivot, tableau: str) -> bytes:
    """Une page du 2033, pour la joindre seule au greffe (bilan, compte de
    résultat). `tableau` est une clé de `PAGES` (`2033A`, `2033B`…)."""
    rendu = PdfLiasse2033Renderer().rendre(liasse)
    lu = PdfReader(io.BytesIO(rendu))
    ecrit = PdfWriter()
    ecrit.add_page(lu.pages[PAGES[tableau] - 1])
    tampon = io.BytesIO()
    ecrit.write(tampon)
    return tampon.getvalue()


class PdfLiasse2033Renderer(FilingRenderer):
    """Exige une `LiassePivot` issue de `cloturer(..., parametres)`."""

    def __init__(self) -> None:
        self._cases = charger_cases()

    def rendre(self, liasse: LiassePivot) -> bytes:
        if "2033B.310" not in liasse.cases:
            raise ValueError("liasse sans cases 2033 : clôturer avec ParametresCloture")
        overlay = OverlayCerfa(CHEMIN_FORMULAIRE_2033)
        self.dessiner(overlay, liasse)
        return overlay.rendre()

    def dessiner(self, overlay: OverlayCerfa, liasse: LiassePivot, decalage_page: int = 0) -> None:
        """Remplit les 7 pages ; `decalage_page` sert quand le 2033 est
        précédé d'autres formulaires dans le même PDF (liasse complète)."""
        for tableau in PAGES:
            self._tableau(overlay, liasse, tableau, decalage_page)
        _entetes(overlay, liasse, decalage_page)
        _net_actif(overlay, liasse, self._cases["1"], decalage_page)
        _capital_2033f(overlay, liasse, self._cases["6"], decalage_page)

    def _tableau(
        self, overlay: OverlayCerfa, liasse: LiassePivot, tableau: str, decalage: int
    ) -> None:
        page = PAGES[tableau]
        cellules = self._cases[str(page)]
        valeurs = _euros(liasse, tableau)
        a_ecrire = {code for code, v in valeurs.items() if v != 0}
        a_ecrire |= set(TOTAUX.get(tableau, ()))
        if tableau == "2033B":
            a_ecrire |= {b for b, d in ALTERNATIVES_2033B if not valeurs.get(d)}
        for code in sorted(a_ecrire & set(cellules)):
            overlay.montant(page + decalage, cellules[code], valeurs.get(code, 0))
        if not any(valeurs.values()) and tableau in ("2033C", "2033D", "2033G"):
            overlay.croix(page + decalage, *NEANT[tableau], taille=TAILLE_CROIX_NEANT)


def _entetes(overlay: OverlayCerfa, liasse: LiassePivot, decalage: int) -> None:
    identite, fin = liasse.identite, liasse.exercice_fin
    debut = liasse.exercice_debut
    if fin is None or debut is None:
        return
    for tableau, (x, y) in DESIGNATION.items():
        if identite is not None:
            overlay.texte(PAGES[tableau] + decalage, x, y, identite.denomination)
    for tableau, (x_jour, x_mois, x_annee, largeur, y) in CLOS_LE_GLYPHES.items():
        page = PAGES[tableau] + decalage
        overlay.cases_regulieres(page, x_jour, largeur, y, f"{fin.day:02d}")
        overlay.cases_regulieres(page, x_mois, largeur, y, f"{fin.month:02d}")
        overlay.cases_regulieres(page, x_annee, largeur, y, f"{fin.year:04d}")
    mois = f"{_duree_mois(debut, fin):02d}"
    _entete_2033a(overlay, identite, mois, 1 + decalage)
    page_e = PAGES["2033E"] + decalage
    overlay.texte(page_e, 96.0, 746.0, debut.strftime("%d/%m/%Y"))
    overlay.texte(page_e, 216.0, 746.0, fin.strftime("%d/%m/%Y"))
    overlay.cases(page_e, (443.8, 458.1, 473.0), 744.5, mois)
    for tableau, gauche in (("2033F", 0.0), ("2033G", 1.0)):
        _entete_f_g(overlay, identite, fin, PAGES[tableau] + decalage, gauche)
    overlay.montant(PAGES["2033G"] + decalage, (306.6, 370.1, 671.4), 0)
    overlay.croix(PAGES["2033G"] + decalage, *NEANT["2033G"], taille=TAILLE_CROIX_NEANT)


def _duree_mois(debut: date, fin: date) -> int:
    """Durée en mois arrondie au mois le plus proche (06/01 → 31/12 = 12)."""
    jours = (fin - debut).days + 1
    return max(1, round(jours * 12 / 365))


SIRET_2033A = (
    88.3,
    103.3,
    117.9,
    132.4,
    147.5,
    162.6,
    177.7,
    192.7,
    207.8,
    222.9,
    237.9,
    253.6,
    268.7,
    283.7,
    298.8,
)


def _entete_2033a(
    overlay: OverlayCerfa, identite: IdentiteEntreprise | None, mois: str, page: int
) -> None:
    overlay.cases(page, (177.7, 192.7, 207.8), 689.0, mois)
    if identite is None:
        return
    overlay.texte_ajuste(page, 134.0, 729.0, identite.adresse_siege.sur_une_ligne(), 430.0)
    overlay.cases(page, SIRET_2033A, 703.0, identite.siret)


# 2033-F et 2033-G ont le même en-tête, décalé d'un point environ :
# bords des cases (F), puis correction pour G.
CLOS_LE_F = (228.1, 243.1, 258.1, 273.0, 288.0, 303.5, 319.0, 334.5, 349.5)
CLOS_LE_G = (229.1, 244.6, 260.1, 275.6, 291.1, 306.6, 322.1, 336.6, 351.5)
SIREN_F = (394.9, 410.4, 425.9, 441.4, 456.9, 471.9, 487.4, 502.4, 517.3, 532.8)
SIREN_G = (400.6, 416.1, 431.1, 446.1, 461.6, 477.1, 492.5, 508.0, 523.5, 539.0)


def _entete_f_g(
    overlay: OverlayCerfa, identite: IdentiteEntreprise | None, fin: date, page: int, g: float
) -> None:
    """`g` = 0 pour le 2033-F, 1 pour le 2033-G (mise en page voisine)."""
    clos, siren = (CLOS_LE_G, SIREN_G) if g else (CLOS_LE_F, SIREN_F)
    y_entete, y_nom, y_voie, y_cp = (
        (737.0, 723.5, 706.8, 689.8) if g else (736.5, 721.5, 703.3, 686.0)
    )
    overlay.cases(page, clos, y_entete, fin.strftime("%d%m%Y"))
    if identite is None:
        return
    adresse = identite.adresse_siege
    overlay.cases(page, siren, y_entete, identite.siren)
    overlay.texte(page, 308.0 if g else 305.0, y_nom, identite.denomination)
    overlay.texte(page, 262.0 if g else 260.0, y_voie, f"{adresse.numero} {adresse.voie}")
    overlay.cases(page, clos[:6], y_cp, adresse.code_postal)
    overlay.texte(page, 372.0 if g else 367.0, y_cp, adresse.commune)


def _net_actif(
    overlay: OverlayCerfa, liasse: LiassePivot, cellules: dict[str, Cellule], decalage: int
) -> None:
    """Colonne 3 du 2033-A : pas de code imprimé, même ligne que le brut,
    à droite de la colonne amortissements."""
    for brut, net in _euros(liasse, "2033A.NET").items():
        if net == 0 and brut not in ("044", "096", "110"):
            continue
        x_gauche, _, y = cellules[brut]
        amortissement = cellules[f"{int(brut) + 2:03d}"] if brut != "044" else cellules["048"]
        if brut in ("096", "110"):
            amortissement = cellules["098" if brut == "096" else "112"]
        overlay.montant(1 + decalage, (amortissement[1], X_DROITE_NET_ACTIF, y), net, gras=False)


# 2033-F cadre II, premier associé personne physique : (x, y) par champ.
ASSOCIE_2033F: dict[str, tuple[float, float]] = {
    "titre": (70.0, 272.5),
    "nom": (216.0, 272.5),
    "prenoms": (413.0, 272.5),
    "detention": (382.0, 254.5),
    "titres": (505.0, 254.5),
    "naissance": (124.0, 236.5),
    "departement": (276.0, 236.5),
    "commune_naissance": (352.0, 236.5),
    "pays_naissance": (490.0, 236.5),
    "numero": (109.0, 217.5),
    "voie": (276.0, 217.5),
    "code_postal": (109.0, 199.5),
    "commune": (276.0, 199.5),
    "pays": (444.0, 199.5),
}


def _capital_2033f(
    overlay: OverlayCerfa, liasse: LiassePivot, cellules: dict[str, Cellule], decalage: int
) -> None:
    identite = liasse.identite
    if identite is None:
        return
    page = PAGES["2033F"] + decalage
    titres = sum(a.nb_titres for a in identite.associes)
    totaux = {"901": 0, "902": 0, "903": len(identite.associes), "904": titres}
    totaux |= {"905": totaux["901"] + totaux["903"], "906": totaux["902"] + totaux["904"]}
    for code, valeur in totaux.items():
        overlay.montant(page, cellules[code], valeur)
    _associes(overlay, page, identite, titres)


def _associes(overlay: OverlayCerfa, page: int, identite: IdentiteEntreprise, titres: int) -> None:
    """Un seul bloc imprimé : au-delà, un état annexe du même modèle serait
    à joindre (renvoi 1 du formulaire) — une SASU/EURL n'a qu'un associé."""
    associe = identite.associes[0]
    part = f"{associe.nb_titres * 100 / titres:.2f}".replace(".", ",")
    champs: dict[str, str] = {
        "titre": associe.civilite,
        "nom": associe.nom,
        "prenoms": associe.prenoms,
        "detention": part,
        "titres": str(associe.nb_titres),
        "naissance": associe.date_naissance.strftime("%d/%m/%Y"),
        "departement": associe.departement_naissance,
        "commune_naissance": associe.commune_naissance,
        "pays_naissance": associe.pays_naissance,
        "numero": associe.adresse.numero,
        "voie": associe.adresse.voie,
        "code_postal": associe.adresse.code_postal,
        "commune": associe.adresse.commune,
        "pays": associe.adresse.pays,
    }
    for champ, valeur in champs.items():
        x, y = ASSOCIE_2033F[champ]
        overlay.texte(page, x, y, valeur)
