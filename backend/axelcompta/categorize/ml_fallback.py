"""Fallback ML — étage 2 (doc 05 §3). Charge le modèle déjà entraîné
(`_AUDIT_DONNEES/modeles/tfidf_logreg_v2.joblib`, gitignoré, présent
seulement sur les postes qui ont fait tourner l'audit ; produit par
`_AUDIT_DONNEES/entrainer_modele.py`, le v1 reste à côté pour revenir en
arrière). Ne l'importe jamais comme code — chargé
comme artefact (doc 03 §3, « personne n'importe ml au runtime »).

Reproduit exactement le featurizing de
`_AUDIT_DONNEES/entrainer_modele.py` (`texte`, `bucket_montant`, identiques
à ceux du v1) : le modèle a été entraîné sur ce format précis, un
featurizing différent donnerait des prédictions incohérentes.

**Signe.** Le modèle a appris sur des montants FEC (charge positive, recette
négative). Une `NormalizedTransaction` suit la convention bancaire (argent
reçu positif, doc 13 §4.1) : le montant est retourné avant le featurizing.
Jusqu'au 2026-09-27 il ne l'était pas, et chaque encaissement était présenté
au modèle comme une dépense.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Protocol

from axelcompta.core.errors import DomaineError

# backend/axelcompta/categorize/ml_fallback.py -> racine du repo
CHEMIN_MODELE_PAR_DEFAUT = (
    Path(__file__).resolve().parents[3] / "_AUDIT_DONNEES" / "modeles" / "tfidf_logreg_v2.joblib"
)


class ModeleMlIndisponible(DomaineError):
    """Le modèle .joblib n'est pas présent sur ce poste (gitignoré) — erreur
    attendue, pas un bug (doc 08 §5)."""


class ModeleSklearn(Protocol):
    """Juste assez du contrat sklearn Pipeline pour ne pas dépendre du type
    concret dans le reste du code (doc 08 §2.6 : pas d'alias mutable partagé,
    ici on type le strict nécessaire)."""

    classes_: Any

    def predict(self, x: list[str]) -> Any: ...
    def predict_proba(self, x: list[str]) -> Any: ...


# Sens possibles d'une catégorie, lus sur le jeu d'entraînement (plus de 95 %
# des lignes dans un seul sens) et conformes au plan comptable : un produit
# n'est jamais un décaissement, une charge jamais un encaissement. Les autres
# catégories (frais bancaires remboursés, cession de véhicule, remboursement
# d'assurance ou de cotisations…) acceptent les deux sens.
ENCAISSEMENTS_SEULEMENT = frozenset({"recettes_plateformes", "subventions"})
DECAISSEMENTS_SEULEMENT = frozenset(
    {
        "a_verifier_location_materiel",
        "abonnements_logiciels",
        "amendes_infractions",
        "assurance_vehicule",
        "carburant",
        "entretien_reparation_vehicule",
        "fournitures_administratives",
        "honoraires_comptable_juridique",
        "interets_emprunts",
        "peage_stationnement",
        "remuneration_dirigeant",
        "repas_et_receptions",
        "sous_traitance_chauffeurs",
        "telecommunications",
        "visite_medicale_vtc",
    }
)


def _bucket_montant(montant_cts: int) -> str:
    """Log-bucket signé, identique à `entrainer_modele_baseline.py`."""
    montant = montant_cts / 100
    if montant == 0:
        return "[M0]"
    signe = "+" if montant > 0 else "-"
    bucket = int(math.log10(abs(montant))) if abs(montant) >= 1 else 0
    return f"[M{signe}{bucket}]"


def texte_pour_modele(libelle: str, montant_cts: int) -> str:
    """`montant_cts` en convention FEC (charge positive), celle de l'entraînement."""
    return f"{libelle} {_bucket_montant(montant_cts)}"


def sens_compatible(categorie: str, montant_bancaire_cts: int) -> bool:
    if montant_bancaire_cts > 0:
        return categorie not in DECAISSEMENTS_SEULEMENT
    if montant_bancaire_cts < 0:
        return categorie not in ENCAISSEMENTS_SEULEMENT
    return True


def charger_modele(chemin: Path | None = None) -> ModeleSklearn:
    chemin = chemin or CHEMIN_MODELE_PAR_DEFAUT
    if not chemin.is_file():
        raise ModeleMlIndisponible(str(chemin))
    import joblib  # import différé : coûteux, inutile si le modèle est absent

    modele: ModeleSklearn = joblib.load(chemin)
    return modele


def predire(modele: ModeleSklearn, libelle: str, montant_cts: int) -> tuple[str, float]:
    """`montant_cts` en convention bancaire (argent reçu positif).

    Les catégories de sens contraire au flux sont écartées. La confiance
    reste la probabilité brute de la catégorie retenue, sans renormaliser :
    si le modèle misait surtout sur une catégorie impossible, la confiance
    baisse et l'étage suivant s'abstient."""
    texte = texte_pour_modele(libelle, -montant_cts)
    probabilites = [float(p) for p in modele.predict_proba([texte])[0]]
    classes = [str(c) for c in modele.classes_]
    candidates = [
        (probabilite, categorie)
        for probabilite, categorie in zip(probabilites, classes, strict=True)
        if sens_compatible(categorie, montant_cts)
    ]
    if not candidates:
        return "non_categorise_a_verifier", 0.0
    confiance, categorie = max(candidates)
    return categorie, confiance
