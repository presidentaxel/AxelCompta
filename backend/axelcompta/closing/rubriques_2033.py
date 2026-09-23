"""Correspondance comptes PCG → rubriques de la liasse 2033 (régime simplifié
d'imposition, notice 2033-NOT-SD millésime 2026).

Résolution par **préfixe le plus long** : `"6712"` l'emporte sur `"67"`.
Un compte de classe 6 ou 7 sans rubrique lève une erreur plutôt que de
tomber dans une ligne « fourre-tout » (doc 08 §2.7) : les préfixes à deux
chiffres ci-dessous couvrent déjà toutes les classes 60 à 79.

Même statut que le mapping catégorie → compte du pack VTC (doc 12 §0.2) :
suit la notice officielle ligne par ligne, mais n'a pas été relu par un
expert-comptable.
"""

from __future__ import annotations

from axelcompta.core.errors import DomaineError


class CompteSansRubrique(DomaineError):
    """Un compte de gestion n'a pas de ligne dans le 2033-B."""


# --- 2033-B : compte de résultat (montant positif = sens normal du poste) ---

PRODUITS_2033B: dict[str, str] = {
    "707": "210",  # ventes de marchandises
    "701": "214",  # production vendue de biens
    "702": "214",
    "703": "214",
    "70": "218",  # production vendue de services (704, 705, 706, 708, 709)
    "71": "222",  # production stockée
    "72": "224",  # production immobilisée
    "73": "230",
    "74": "226",  # subventions d'exploitation
    "75": "230",  # autres produits
    "78": "230",  # reprises d'exploitation
    "79": "230",  # transferts de charges
    "76": "280",  # produits financiers
    "786": "280",
    "796": "280",
    "77": "290",  # produits exceptionnels
    "787": "290",
    "797": "290",
}

CHARGES_2033B: dict[str, str] = {
    "607": "234",  # achats de marchandises
    "6087": "234",
    "6097": "234",
    "6037": "236",  # variation de stock de marchandises
    "601": "238",  # matières premières et approvisionnements
    "602": "238",
    "6081": "238",
    "6082": "238",
    "6091": "238",
    "6092": "238",
    "6031": "240",  # variation de stock matières
    "6032": "240",
    "60": "242",  # 604, 605, 606 (carburant 6061...) : autres charges externes
    "61": "242",
    "62": "242",
    "63": "244",  # impôts, taxes et versements assimilés
    "641": "250",  # rémunérations du personnel
    "644": "250",
    "64": "252",  # charges sociales
    "6811": "254",  # dotations aux amortissements
    "6812": "254",
    "68": "256",  # dotations aux dépréciations et provisions
    "686": "294",
    "687": "300",
    "65": "262",  # autres charges
    "66": "294",  # charges financières
    "67": "300",  # charges exceptionnelles
    "69": "306",  # impôt sur les bénéfices
}

# Charges non déductibles réintégrées au résultat fiscal (2033-B cadre B).
# L'IS lui-même (69x → 306) est réintégré ligne 324 par le calcul, pas ici.
REINTEGRATIONS_2033B: dict[str, str] = {
    "6712": "330",  # pénalités, amendes fiscales et pénales (CGI art. 39-2)
}

# --- 2033-A : bilan ---------------------------------------------------------

# Postes d'actif quel que soit le sens du solde : (colonne brut, colonne
# amortissements/provisions). Les comptes 28/29/39/49/59 sont des
# soustractifs : leur solde créditeur va en colonne 2.
ACTIF_BRUT_2033A: dict[str, str] = {
    "207": "010",
    "20": "014",
    "232": "014",
    "237": "014",
    "21": "028",
    "22": "028",
    "23": "028",
    "26": "040",
    "27": "040",
    "31": "050",
    "32": "050",
    "33": "050",
    "34": "050",
    "35": "050",
    "37": "060",
    "3": "050",  # 36, 38 : autres stocks et en-cours
    "4091": "064",
    "411": "068",
    "413": "068",
    "416": "068",
    "418": "068",
    "486": "092",
    "50": "080",
}

ACTIF_SOUSTRACTIF_2033A: dict[str, str] = {
    "2807": "012",
    "2907": "012",
    "280": "016",
    "290": "016",
    "281": "030",
    "282": "030",
    "291": "030",
    "293": "030",
    "296": "042",
    "297": "042",
    "39": "052",
    "397": "062",
    "491": "070",
    "496": "074",
    "59": "082",
}

# Postes de passif quel que soit le sens du solde (montant = solde créditeur).
PASSIF_2033A: dict[str, str] = {
    "10": "120",  # capital (1013...), sauf les réserves 106 ci-dessous
    "101": "120",
    "104": "120",
    "108": "120",
    "105": "124",
    "1061": "126",
    "1064": "130",
    "106": "132",  # 1063 statutaires, 1068 autres réserves
    "11": "134",
    "12": "136",
    "13": "137",
    "14": "140",
    "15": "154",
    "16": "156",
    "17": "156",
    "4191": "164",
    "401": "166",
    "403": "166",
    "404": "166",
    "405": "166",
    "408": "166",
    "487": "174",
}

# Postes dont le côté dépend du signe du solde : (poste si débiteur, poste
# si créditeur). Une banque débitrice est une disponibilité, créditrice un
# concours bancaire ; une TVA débitrice une créance, créditrice une dette.
SELON_SIGNE_2033A: dict[str, tuple[str, str]] = {
    "51": ("084", "156"),
    "53": ("084", "156"),
    "54": ("084", "156"),
    "42": ("072", "172"),
    "43": ("072", "172"),
    "44": ("072", "172"),
    "455": ("072", "173"),
    "4": ("072", "175"),
    "5": ("084", "156"),  # 52, 58 : trésorerie et virements internes
}


def rubrique(compte: str, table: dict[str, str]) -> str | None:
    """Préfixe le plus long de `compte` présent dans `table`."""
    for longueur in range(len(compte), 0, -1):
        code = table.get(compte[:longueur])
        if code is not None:
            return code
    return None


def rubrique_selon_signe(compte: str) -> tuple[str, str] | None:
    for longueur in range(len(compte), 0, -1):
        paire = SELON_SIGNE_2033A.get(compte[:longueur])
        if paire is not None:
            return paire
    return None


def rubrique_resultat(compte: str) -> tuple[str, int]:
    """(code 2033-B, signe) : +1 pour une charge (solde débiteur positif),
    -1 pour un produit (solde créditeur rendu positif)."""
    table, signe = (CHARGES_2033B, 1) if compte.startswith("6") else (PRODUITS_2033B, -1)
    code = rubrique(compte, table)
    if code is None:
        raise CompteSansRubrique(f"compte {compte} : aucune ligne du 2033-B")
    return code, signe
