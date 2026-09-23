"""Tableaux 2033-A (bilan) et 2033-B (compte de résultat et résultat fiscal)
calculés depuis la balance de clôture (notice 2033-NOT-SD, millésime 2026).

Montants en **euros entiers**, comme sur le formulaire : chaque rubrique
est arrondie une fois, puis les totaux sont des sommes de rubriques
arrondies (jamais un total arrondi à part, qui pourrait ne plus tomber
juste). L'écart d'arrondi du bilan, s'il y en a un, est absorbé par la
rubrique la plus proche de sa valeur exacte (`_repartir_ecart`) et exposé
à part (`ECART_ARRONDI`).

Clé des dictionnaires = code de la case sur le formulaire officiel.
"""

from __future__ import annotations

from collections import defaultdict

from axelcompta.core.errors import DomaineError
from axelcompta.core.pcg import nature_depuis_compte

from .impot_societes import arrondir_euros
from .rubriques_2033 import (
    ACTIF_BRUT_2033A,
    ACTIF_SOUSTRACTIF_2033A,
    PASSIF_2033A,
    REINTEGRATIONS_2033B,
    CompteSansRubrique,
    rubrique,
    rubrique_resultat,
    rubrique_selon_signe,
)

Balance = dict[str, int]  # compte → solde en centimes, débiteur positif


class BilanDesequilibre(DomaineError):
    """Actif net et passif diffèrent de plus que l'arrondi à l'euro."""


PRODUITS_EXPLOITATION = ("210", "214", "218", "222", "224", "226", "230")
CHARGES_EXPLOITATION = ("234", "236", "238", "240", "242", "244", "250", "252", "254", "256", "262")
REINTEGRATIONS = ("316", "318", "322", "324", "330", "251")
DEDUCTIONS = ("342", "350")

# (brut, amortissements) par ligne d'actif ; le net (colonne 3) s'en déduit.
LIGNES_ACTIF = (
    ("010", "012"),
    ("014", "016"),
    ("028", "030"),
    ("040", "042"),
    ("050", "052"),
    ("060", "062"),
    ("064", "066"),
    ("068", "070"),
    ("072", "074"),
    ("092", "094"),
    ("080", "082"),
    ("084", "086"),
)
IMMOBILISE = LIGNES_ACTIF[:4]
CIRCULANT = LIGNES_ACTIF[4:]
CAPITAUX_PROPRES = ("120", "124", "126", "130", "132", "134", "136", "137", "140")
DETTES = ("156", "164", "166", "172", "173", "175", "174")


def _arrondir(lignes: dict[str, int]) -> dict[str, int]:
    return {code: arrondir_euros(centimes) for code, centimes in lignes.items()}


def _somme(lignes: dict[str, int], codes: tuple[str, ...]) -> int:
    return sum(lignes.get(code, 0) for code in codes)


def compte_de_resultat(balance: Balance) -> dict[str, int]:
    """2033-B cadre A. 306 = IS comptabilisé (compte 69x) s'il y en a un."""
    centimes: dict[str, int] = defaultdict(int)
    for compte, solde in balance.items():
        if nature_depuis_compte(compte) == "autre":
            continue
        code, signe = rubrique_resultat(compte)
        centimes[code] += signe * solde
    lignes = _arrondir(centimes)
    lignes["232"] = _somme(lignes, PRODUITS_EXPLOITATION)
    lignes["264"] = _somme(lignes, CHARGES_EXPLOITATION)
    lignes["270"] = lignes["232"] - lignes["264"]
    produits = lignes["232"] + _somme(lignes, ("280", "290"))
    charges = lignes["264"] + _somme(lignes, ("294", "300", "306"))
    lignes["310"] = produits - charges
    return lignes


def _reintegrations(balance: Balance, impot_comptabilise: int) -> dict[str, int]:
    centimes: dict[str, int] = defaultdict(int)
    for compte, solde in balance.items():
        code = rubrique(compte, REINTEGRATIONS_2033B)
        if code is not None:
            centimes[code] += solde
    lignes = _arrondir(centimes)
    # Notice, ligne 324 : l'impôt sur les sociétés lui-même n'est pas déductible.
    lignes["324"] = lignes.get("324", 0) + impot_comptabilise
    return lignes


def resultat_fiscal(
    resultat: dict[str, int], balance: Balance, deficits_anterieurs: int = 0
) -> dict[str, int]:
    """2033-B cadre B. `deficits_anterieurs` : 2033-D ligne 870 de
    l'exercice précédent, imputé dans la limite du bénéfice (et d'1 M€ +
    50 % au-delà, CGI art. 209-I, sans objet à cette échelle)."""
    lignes = _reintegrations(balance, resultat.get("306", 0))
    comptable = resultat["310"]
    lignes["312"] = max(comptable, 0)
    lignes["314"] = max(-comptable, 0)
    avant_deficits = comptable + _somme(lignes, REINTEGRATIONS) - _somme(lignes, DEDUCTIONS)
    lignes["352"] = max(avant_deficits, 0)
    lignes["354"] = max(-avant_deficits, 0)
    lignes["360"] = min(deficits_anterieurs, lignes["352"])
    lignes["370"] = lignes["352"] - lignes["360"]
    lignes["372"] = lignes["354"]
    return lignes


def _poste_bilan(compte: str, solde: int) -> tuple[str, int] | None:
    """(code 2033-A, montant positif dans le sens du poste), ou `None` pour
    un compte de gestion (classes 6/7, repris via le résultat 136)."""
    if nature_depuis_compte(compte) != "autre":
        return None
    for table, signe in ((ACTIF_SOUSTRACTIF_2033A, -1), (ACTIF_BRUT_2033A, 1), (PASSIF_2033A, -1)):
        code = rubrique(compte, table)
        if code is not None:
            return code, signe * solde
    paire = rubrique_selon_signe(compte)
    if paire is None:
        raise CompteSansRubrique(f"compte {compte} : aucun poste du 2033-A")
    return (paire[0], solde) if solde >= 0 else (paire[1], -solde)


def _detail_bilan(balance: Balance) -> tuple[dict[str, int], int]:
    """(rubriques en centimes, TVA incluse dans les dettes fiscales 172)."""
    centimes: dict[str, int] = defaultdict(int)
    tva = 0
    for compte, solde in balance.items():
        poste = _poste_bilan(compte, solde)
        if poste is None:
            continue
        code, montant = poste
        centimes[code] += montant
        if code == "172" and compte.startswith("445"):
            tva += montant
    return centimes, tva


def _totaux_actif(lignes: dict[str, int]) -> None:
    for groupe, total_brut, total_amort in ((IMMOBILISE, "044", "048"), (CIRCULANT, "096", "098")):
        lignes[total_brut] = sum(lignes.get(brut, 0) for brut, _ in groupe)
        lignes[total_amort] = sum(lignes.get(amort, 0) for _, amort in groupe)
    lignes["110"] = lignes["044"] + lignes["096"]
    lignes["112"] = lignes["048"] + lignes["098"]


def _totaux_passif(lignes: dict[str, int]) -> None:
    lignes["142"] = _somme(lignes, CAPITAUX_PROPRES)
    lignes["176"] = _somme(lignes, DETTES)
    lignes["180"] = lignes["142"] + lignes.get("154", 0) + lignes["176"]


def _repartir_ecart(lignes: dict[str, int], centimes: dict[str, int], ecart: int) -> None:
    """Absorbe l'écart d'arrondi (actif net - passif, en euros) dans la
    rubrique existante que la correction éloigne le moins de sa valeur au
    centime : un bilan à 846,50 € de découvert s'écrit 846 plutôt que 847,
    sans créer de ligne « autres créances » de 1 € qui n'existe pas."""
    actif = {brut for brut, _ in LIGNES_ACTIF}
    candidats: list[tuple[int, str, int]] = []
    for code, exact in centimes.items():
        if not exact or code == "136":
            continue
        # Actif trop fort (écart > 0) : baisser l'actif ou monter le passif.
        correction = -ecart if code in actif else ecart
        ajuste = lignes[code] + correction
        candidats.append((abs(ajuste * 100 - exact), code, ajuste))
    if not candidats:
        raise BilanDesequilibre(f"écart d'arrondi de {ecart} € sans rubrique pour l'absorber")
    _, code, ajuste = min(candidats)
    lignes[code] = ajuste


def bilan(balance: Balance, resultat_exercice: int) -> dict[str, int]:
    """2033-A. `resultat_exercice` = 2033-B ligne 310, repris en 136 : le
    même chiffre des deux côtés, pas un recalcul qui pourrait diverger d'un
    euro d'arrondi."""
    centimes, tva = _detail_bilan(balance)
    lignes = _arrondir(centimes)
    lignes["136"] = resultat_exercice
    lignes["169"] = arrondir_euros(tva)
    lignes["199"] = arrondir_euros(
        sum(s for c, s in balance.items() if c.startswith("455") and s > 0)
    )
    _totaux_actif(lignes)
    _totaux_passif(lignes)
    ecart = (lignes["110"] - lignes["112"]) - lignes["180"]
    # Au plus 1 € par rubrique arrondie : au-delà, ce n'est plus un arrondi
    # mais un bilan faux (doc 08 §2.7 : on s'arrête, on ne masque pas).
    if abs(ecart) > len(centimes) + 1:
        raise BilanDesequilibre(f"actif net - passif = {ecart} € (hors arrondi)")
    if ecart:
        _repartir_ecart(lignes, centimes, ecart)
        _totaux_actif(lignes)
        _totaux_passif(lignes)
    lignes["ECART_ARRONDI"] = ecart
    return lignes


def net_actif(lignes: dict[str, int]) -> dict[str, int]:
    """Colonne 3 (net) de l'actif, indexée par le code de la colonne brut ;
    plus les totaux I (044), II (096) et général (110)."""
    paires = LIGNES_ACTIF + (("044", "048"), ("096", "098"), ("110", "112"))
    return {brut: lignes.get(brut, 0) - lignes.get(amort, 0) for brut, amort in paires}
