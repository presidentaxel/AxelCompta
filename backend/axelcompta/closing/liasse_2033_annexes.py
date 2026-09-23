"""Tableaux annexes 2033-C (immobilisations), 2033-D (déficits, divers) et
2033-E (effectifs, valeur ajoutée), notice 2033-NOT-SD millésime 2026.

Les tableaux 2033-F (capital) et 2033-G (filiales) ne sont pas calculés
ici : ils viennent de l'identité du dossier, pas de sa comptabilité.
Euros entiers, même règle d'arrondi que `liasse_2033`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from axelcompta.ledger.models import Ecriture, Journal, Sens

from .impot_societes import arrondir_euros
from .liasse_2033 import Balance
from .rubriques_2033 import rubrique

# --- Mouvements -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Mouvements:
    """Par compte, en centimes : solde d'ouverture (journal AN), débits et
    crédits de l'exercice hors à-nouveaux."""

    ouverture: dict[str, int]
    debits: dict[str, int]
    credits: dict[str, int]


def mouvements(ecritures: tuple[Ecriture, ...]) -> Mouvements:
    ouverture: dict[str, int] = defaultdict(int)
    debits: dict[str, int] = defaultdict(int)
    credits: dict[str, int] = defaultdict(int)
    for ecriture in ecritures:
        for ligne in ecriture.lignes:
            montant = ligne.montant.centimes
            if ecriture.journal is Journal.AN:
                ouverture[ligne.compte] += montant if ligne.sens is Sens.DEBIT else -montant
            elif ligne.sens is Sens.DEBIT:
                debits[ligne.compte] += montant
            else:
                credits[ligne.compte] += montant
    return Mouvements(dict(ouverture), dict(debits), dict(credits))


# --- 2033-C : immobilisations et amortissements -----------------------------

# Code de la colonne « début » ; les trois colonnes suivantes (augmentations,
# diminutions, fin) sont début + 2, + 4, + 6 sur le formulaire.
IMMOBILISATIONS_2033C: dict[str, str] = {
    "207": "400",
    "20": "410",
    "211": "420",
    "212": "420",
    "213": "430",
    "214": "430",
    "215": "440",
    "2181": "450",
    "2182": "460",
    "21": "470",
    "22": "470",
    "23": "470",
    "26": "480",
    "27": "480",
}
AMORTISSEMENTS_2033C: dict[str, str] = {
    "2807": "495",
    "280": "500",
    "2811": "510",
    "2812": "510",
    "2813": "520",
    "2814": "520",
    "2815": "530",
    "28181": "540",
    "28182": "550",
    "281": "560",
    "282": "560",
}


def _code(debut: str, decalage: int) -> str:
    # Seule exception du formulaire : la ligne « fonds commercial » des
    # amortissements est numérotée 495, 497, 498, 499.
    if debut == "495":
        return {0: "495", 2: "497", 4: "498", 6: "499"}[decalage]
    return f"{int(debut) + decalage:03d}"


def _tableau_c(table: dict[str, str], m: Mouvements, sens: int) -> dict[str, int]:
    """`sens` = +1 pour des immobilisations (débit = augmentation), -1 pour
    des amortissements (crédit = dotation)."""
    centimes: dict[str, int] = defaultdict(int)
    comptes = set(m.ouverture) | set(m.debits) | set(m.credits)
    for compte in comptes:
        debut = rubrique(compte, table)
        if debut is None or not compte.startswith("2"):
            continue
        hausse, baisse = (m.debits, m.credits) if sens > 0 else (m.credits, m.debits)
        centimes[debut] += sens * m.ouverture.get(compte, 0)
        centimes[_code(debut, 2)] += hausse.get(compte, 0)
        centimes[_code(debut, 4)] += baisse.get(compte, 0)
    lignes = {code: arrondir_euros(v) for code, v in centimes.items()}
    for debut in set(table.values()):
        if debut in lignes:
            fin = lignes[debut] + lignes[_code(debut, 2)] - lignes[_code(debut, 4)]
            lignes[_code(debut, 6)] = fin
    return lignes


def immobilisations_2033c(m: Mouvements) -> dict[str, int]:
    """Cadres I et II. Vide (`{}`) sans aucune immobilisation : le tableau
    est alors déposé « Néant ». Cadre III (plus-values) : les cessions ne
    sont pas encore modélisées (pas de registre des immobilisations)."""
    lignes = _tableau_c(IMMOBILISATIONS_2033C, m, 1) | _tableau_c(AMORTISSEMENTS_2033C, m, -1)
    if not lignes:
        return {}
    for total, debuts in (
        ("490", ("400", "410", "420", "430", "440", "450", "460", "470", "480")),
        ("570", ("495", "500", "510", "520", "530", "540", "550", "560")),
    ):
        for decalage in (0, 2, 4, 6):
            lignes[_code(total, decalage)] = sum(lignes.get(_code(d, decalage), 0) for d in debuts)
    return lignes


# --- 2033-D : déficits reportables et divers --------------------------------


def releve_2033d(
    balance_avant_cloture: Balance,
    m: Mouvements,
    resultat_fiscal: dict[str, int],
    deficits_anterieurs: int,
) -> dict[str, int]:
    """Cadre II (déficits) et cadre III (TVA, prélèvements). TVA lue sur la
    balance **avant** l'écriture de liquidation, qui solde 4456/4457."""
    collectee = -sum(s for c, s in balance_avant_cloture.items() if c.startswith("4457"))
    deductible = sum(
        s
        for c, s in balance_avant_cloture.items()
        if c.startswith("4456") and not c.startswith("44562")  # 44562 : immobilisations
    )
    # Dépenses personnelles du dirigeant reclassées au débit de son compte
    # courant (455) : les « prélèvements » de la ligne 399.
    prelevements = sum(v for c, v in m.debits.items() if c.startswith("455"))
    imputes = resultat_fiscal.get("360", 0)
    lignes = {
        "374": arrondir_euros(collectee),
        "378": arrondir_euros(deductible),
        "399": arrondir_euros(prelevements),
        "982": deficits_anterieurs,
        "983": imputes,
        "984": deficits_anterieurs - imputes,
        "860": resultat_fiscal.get("372", 0),
    }
    lignes["870"] = lignes["984"] + lignes["860"]
    return lignes


# --- 2033-E : valeur ajoutée ------------------------------------------------

# Charges à retenir (cadre III). Les loyers 612/613 ne sont pas déduits :
# ceux du pack VTC sont des LOA/locations longue durée (> 6 mois), exclues
# de la ligne 310 par la notice.
CHARGES_VA_2033E: dict[str, str] = {
    "60": "121",
    "6037": "145",
    "603": "145",
    "61": "125",
    "62": "125",
    "612": "",
    "613": "",
    "63": "133",
    "65": "148",
}
PRODUITS_VA_2033E: dict[str, str] = {
    "70": "108",
    "709": "108",
    "72": "143",
    "74": "113",
    "75": "115",
}


def _cumul(balance: Balance, table: dict[str, str], signe: int) -> dict[str, int]:
    centimes: dict[str, int] = defaultdict(int)
    for compte, solde in balance.items():
        code = rubrique(compte, table)
        if code:
            centimes[code] += signe * solde
    return {code: arrondir_euros(v) for code, v in centimes.items()}


def valeur_ajoutee_2033e(balance: Balance, effectif_moyen: int = 0) -> dict[str, int]:
    lignes = {"376": effectif_moyen}
    lignes |= _cumul(balance, PRODUITS_VA_2033E, -1)
    lignes |= _cumul(balance, CHARGES_VA_2033E, 1)
    lignes["106"] = sum(lignes.get(c, 0) for c in ("108", "118", "119"))
    lignes["144"] = sum(lignes.get(c, 0) for c in ("115", "143", "113", "111", "153"))
    lignes["152"] = sum(
        lignes.get(c, 0) for c in ("121", "145", "125", "310", "133", "148", "128", "135", "150")
    )
    lignes["137"] = lignes["106"] + lignes["144"] - lignes["152"]
    # Notice, ligne 117 : une valeur ajoutée négative se déclare à 0.
    lignes["117"] = max(lignes["137"], 0)
    return lignes
