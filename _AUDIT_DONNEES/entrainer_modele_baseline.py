"""Entraîne le modèle baseline TF-IDF + régression logistique (doc 07 §3.2,
doc 12 §0.3 — spike ML) sur les catégories dérivées du mapping compte PCG.

**Important — ce que cette évaluation mesure et ce qu'elle NE mesure PAS :**
Les labels d'entraînement viennent du mapping compte PCG -> catégorie
(construire_taxonomie.py), pas d'une relecture humaine. L'exactitude
rapportée ici mesure donc « le modèle généralise-t-il le mapping à des
libellés et des dossiers qu'il n'a jamais vus », pas « le modèle a-t-il
raison dans l'absolu ». C'est un signal utile (si le split par dossier était
mauvais, même ça échouerait), mais **pas un remplacement du jeu de test gelé
de 500 lignes relues à la main** (voir generer_echantillon_relecture.py) :
tant que sa colonne `categorie_validee` n'est pas remplie, aucune vraie
mesure de précision n'existe.

Split par dossier (pas aléatoire ligne à ligne) pour éviter la fuite : un
même dossier a des habitudes de libellé répétitives (même carte, mêmes
enseignes) qui donneraient une exactitude gonflée si mélangées entre train
et test (doc 07 §"splits par dossier ET période").

**Transactions composites exclues de l'entraînement** (voir
construire_taxonomie.py §2) : quand un même piece_ref porte plusieurs
catégories (ex. commission + recette d'un même settlement plateforme), les
lignes qui en sortent partagent le même libellé bancaire pour des catégories
différentes — un signal contradictoire pour un modèle texte -> catégorie.
Les garder fausserait l'entraînement pour un gain nul : cette distinction-là
(commission vs recette) est de toute façon déjà déterministe par le
template comptable (doc 06 §3.5, doc 13 §5.3), pas quelque chose à apprendre
du libellé.

**Feature montant ajoutée** (doc 07 §3.1 : "Montant (log-bucketé) + signe").
Contrairement au token compte-PCG d'ADR-007 (pas disponible à l'inférence
sur une transaction brute, voir rapport_audit_dataset.md §6), le montant
EST disponible dès la réception d'une transaction bancaire réelle — feature
légitime, pas de fuite. Objectif : aider les catégories où le libellé seul
est trop générique pour trancher (`remuneration_dirigeant` en particulier :
"000001 VIR EUROPEEN" ne dit rien, mais un virement récurrent de plusieurs
milliers d'euros est un signal fort).

Usage:
    python entrainer_modele_baseline.py
"""
import csv
import math
import random
from collections import Counter
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline

ENTREE = Path("resultats/fec_ml_taxonomie.csv")
SORTIE_MODELE = Path("modeles/tfidf_logreg_v1.joblib")
SORTIE_RAPPORT = Path("resultats/rapport_baseline_ml.txt")

# Catégories hors périmètre ML : pas des transactions bancaires (générées à
# la clôture) ou pas des catégories de dépense (mouvements de capital), ou
# bucket technique du mapping (compte pas encore mappé).
EXCLUES = {
    "dotations_amortissements", "operation_capital_hors_perimetre",
    "non_categorise_a_verifier",
}
SEED = 20260902
MIN_EXEMPLES_PAR_CLASSE = 15  # sous ce seuil, pas assez pour split train/test


def bucket_montant(montant_str: str) -> str:
    """Log-bucket signé : '[M+2]' = positif, dizaine de milliers de log10."""
    try:
        m = float(montant_str)
    except (ValueError, TypeError):
        return "[M?]"
    if m == 0:
        return "[M0]"
    signe = "+" if m > 0 else "-"
    bucket = int(math.log10(abs(m))) if abs(m) >= 1 else 0
    return f"[M{signe}{bucket}]"


def texte_avec_montant(row: dict) -> str:
    return f"{row['libelle_bancaire']} {bucket_montant(row['montant'])}"


def main() -> None:
    random.seed(SEED)
    rows = []
    with ENTREE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["categorie"] in EXCLUES or not row["libelle_bancaire"].strip():
                continue
            if row.get("type_transaction") == "composite":
                continue
            rows.append(row)

    compte_classes = Counter(r["categorie"] for r in rows)
    classes_retenues = {c for c, n in compte_classes.items() if n >= MIN_EXEMPLES_PAR_CLASSE}
    classes_ecartees = {c: n for c, n in compte_classes.items() if n < MIN_EXEMPLES_PAR_CLASSE}
    rows = [r for r in rows if r["categorie"] in classes_retenues]

    # split par dossier : 80% des dossiers en train, 20% en test
    dossiers = sorted({r["dossier_id"] for r in rows})
    random.shuffle(dossiers)
    n_test = max(1, int(len(dossiers) * 0.2))
    dossiers_test = set(dossiers[:n_test])

    train = [r for r in rows if r["dossier_id"] not in dossiers_test]
    test = [r for r in rows if r["dossier_id"] in dossiers_test]

    X_train = [texte_avec_montant(r) for r in train]
    y_train = [r["categorie"] for r in train]
    X_test = [texte_avec_montant(r) for r in test]
    y_test = [r["categorie"] for r in test]

    # n-grammes de caractères : les libellés sont courts, tronqués et bruités
    # ("CARTE X8651 03/04 RE") — les mots entiers seuls perdent trop de signal.
    # Le token [M+3] (bucket de montant) reste intact grâce à char_wb (word
    # boundaries) : il n'est jamais fusionné avec le texte du libellé.
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    rapport = classification_report(y_test, y_pred, zero_division=0)

    SORTIE_MODELE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, SORTIE_MODELE)

    with SORTIE_RAPPORT.open("w", encoding="utf-8") as f:
        f.write("Baseline TF-IDF (char 2-4-grammes, libellé + bucket montant) + LogReg\n")
        f.write("Labels = mapping compte PCG -> catégorie, PAS relecture humaine.\n")
        f.write("Transactions composites (piece_ref multi-catégorie) exclues de l'entraînement.\n")
        f.write(f"Dossiers train : {len(dossiers) - n_test} | dossiers test : {n_test}\n")
        f.write(f"Exemples train : {len(train)} | exemples test : {len(test)}\n")
        f.write(f"Classes retenues (>= {MIN_EXEMPLES_PAR_CLASSE} ex.) : {len(classes_retenues)}\n")
        f.write(f"Classes écartées (trop peu d'exemples) : {classes_ecartees}\n\n")
        f.write(f"Exactitude (test, dossiers jamais vus, vs labels dérivés du mapping) : {acc*100:.1f}%\n\n")
        f.write(rapport)

    print(f"Exactitude sur dossiers non vus : {acc*100:.1f}% "
          f"(mesurée contre les labels du mapping, pas contre une relecture humaine)")
    print(f"Modèle -> {SORTIE_MODELE}")
    print(f"Rapport détaillé -> {SORTIE_RAPPORT}")


if __name__ == "__main__":
    main()
