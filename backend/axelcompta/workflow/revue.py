"""Résolution d'une écriture « à trancher » par une décision humaine (doc 17
§9 bloc C). Prend une écriture déjà posée sur le compte d'attente (471,
doc 06 §2) et la catégorie choisie par l'humain, produit l'écriture réelle
correspondante — montants et sens de chaque ligne inchangés, seul le compte
de contrepartie change. Une reclassification, jamais un nouveau calcul.
"""

from __future__ import annotations

import dataclasses

from axelcompta.ledger.contrepassation import origine
from axelcompta.ledger.models import Ecriture

from .decisions import DecisionHumaine

COMPTE_ATTENTE = "471"
CATEGORIE_USAGE_PERSONNEL = "usage_personnel"


class CategorieInconnueError(ValueError):
    """La catégorie choisie n'a ni compte dans le pack ni traitement spécial
    connu — pas de repli silencieux (doc 08 §2.7)."""


def resoudre_ecriture_a_trancher(
    ecriture: Ecriture,
    categorie_choisie: str,
    compte_usage_personnel: str | None,
    comptes_par_categorie: dict[str, str],
) -> Ecriture:
    """Remplace le compte d'attente par le compte réel correspondant à la
    décision humaine. Lève `CategorieInconnueError` plutôt que de deviner un
    compte — une décision qu'on ne sait pas traduire est un bug à corriger,
    pas un cas à masquer.

    `compte_usage_personnel` vient de la colonne du dossier dans la matrice
    (doc 06 §3.6, §7 : 455 pour une société, 108 pour une EI, aucun pour une
    micro-entreprise, où l'usage personnel est signalé sans écriture)."""
    compte_cible = _compte_cible(categorie_choisie, compte_usage_personnel, comptes_par_categorie)
    lignes = tuple(
        dataclasses.replace(ligne, compte=compte_cible) if ligne.compte == COMPTE_ATTENTE else ligne
        for ligne in ecriture.lignes
    )
    return dataclasses.replace(ecriture, lignes=lignes)


def _compte_cible(
    categorie_choisie: str,
    compte_usage_personnel: str | None,
    comptes_par_categorie: dict[str, str],
) -> str:
    if categorie_choisie == CATEGORIE_USAGE_PERSONNEL:
        if compte_usage_personnel is None:
            raise CategorieInconnueError(
                "pour ce statut, l'usage personnel est signalé sans écriture (doc 06 §7)"
            )
        return compte_usage_personnel
    compte = comptes_par_categorie.get(categorie_choisie)
    if compte is None:
        raise CategorieInconnueError(f"catégorie inconnue du pack : {categorie_choisie!r}")
    return compte


def appliquer_decisions(
    ecritures: tuple[Ecriture, ...],
    decisions: tuple[DecisionHumaine, ...],
    compte_usage_personnel: str | None,
    comptes_par_categorie: dict[str, str],
) -> tuple[Ecriture, ...]:
    """Le grand livre tel que les décisions humaines le disent : chaque
    écriture tranchée prend son compte réel, les autres restent telles
    quelles. Les écritures en base ne changent jamais (append-only, doc 06
    §1) : la décision est une couche lue par-dessus. La dernière décision
    d'une écriture l'emporte, et une contre-passation suit celle de son
    originale, sinon son 471 resterait ouvert."""
    dernieres = {decision.ecriture_id: decision for decision in decisions}
    resultat = []
    for ecriture in ecritures:
        decision = dernieres.get(origine(ecriture.id) or ecriture.id)
        if decision is not None:
            ecriture = resoudre_ecriture_a_trancher(
                ecriture, decision.categorie, compte_usage_personnel, comptes_par_categorie
            )
        resultat.append(ecriture)
    return tuple(resultat)
