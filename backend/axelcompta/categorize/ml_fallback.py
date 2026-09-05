"""Fallback ML — étage 2 (doc 05 §3). Charge le modèle déjà entraîné
(`_AUDIT_DONNEES/modeles/tfidf_logreg_v1.joblib`, gitignoré, présent
seulement sur les postes qui ont fait tourner l'audit), **aucun
réentraînement** (doc 17 §4bis). Ne l'importe jamais comme code — chargé
comme artefact (doc 03 §3, « personne n'importe ml au runtime »).

Reproduit exactement le featurizing de
`_AUDIT_DONNEES/entrainer_modele_baseline.py` (`texte_avec_montant`,
`bucket_montant`) : le modèle a été entraîné sur ce format précis, un
featurizing différent donnerait des prédictions incohérentes.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Protocol

from axelcompta.core.errors import DomaineError

# backend/axelcompta/categorize/ml_fallback.py -> racine du repo
CHEMIN_MODELE_PAR_DEFAUT = (
    Path(__file__).resolve().parents[3] / "_AUDIT_DONNEES" / "modeles" / "tfidf_logreg_v1.joblib"
)


class ModeleMlIndisponible(DomaineError):
    """Le modèle .joblib n'est pas présent sur ce poste (gitignoré) — erreur
    attendue, pas un bug (doc 08 §5)."""


class ModeleSklearn(Protocol):
    """Juste assez du contrat sklearn Pipeline pour ne pas dépendre du type
    concret dans le reste du code (doc 08 §2.6 : pas d'alias mutable partagé,
    ici on type le strict nécessaire)."""

    def predict(self, x: list[str]) -> Any: ...
    def predict_proba(self, x: list[str]) -> Any: ...


def _bucket_montant(montant_cts: int) -> str:
    """Log-bucket signé, identique à `entrainer_modele_baseline.py`."""
    montant = montant_cts / 100
    if montant == 0:
        return "[M0]"
    signe = "+" if montant > 0 else "-"
    bucket = int(math.log10(abs(montant))) if abs(montant) >= 1 else 0
    return f"[M{signe}{bucket}]"


def texte_pour_modele(libelle: str, montant_cts: int) -> str:
    return f"{libelle} {_bucket_montant(montant_cts)}"


def charger_modele(chemin: Path | None = None) -> ModeleSklearn:
    chemin = chemin or CHEMIN_MODELE_PAR_DEFAUT
    if not chemin.is_file():
        raise ModeleMlIndisponible(str(chemin))
    import joblib  # import différé : coûteux, inutile si le modèle est absent

    modele: ModeleSklearn = joblib.load(chemin)
    return modele


def predire(modele: ModeleSklearn, libelle: str, montant_cts: int) -> tuple[str, float]:
    texte = texte_pour_modele(libelle, montant_cts)
    categorie = str(modele.predict([texte])[0])
    confiance = float(max(modele.predict_proba([texte])[0]))
    return categorie, confiance
