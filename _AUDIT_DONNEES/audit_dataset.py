"""Audit du dataset historique — voir README.md et doc 07 §2.1.

Usage:
    python audit_dataset.py --transactions transactions.csv --step all
    python audit_dataset.py --transactions transactions.csv --step distribution-classes --n-min 100

Dépendances : pandas, scikit-learn, joblib (pip install pandas scikit-learn joblib)
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).parent / "sortie"


def load_transactions(path: str, cols: dict) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in cols.values() if c not in df.columns]
    if missing:
        sys.exit(f"Colonnes manquantes dans {path} : {missing}")
    df = df.rename(columns={v: k for k, v in cols.items()})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def step_inventaire(df: pd.DataFrame, out: Path):
    report = {
        "n_lignes": len(df),
        "n_dossiers": df["dossier_id"].nunique(),
        "periode_min": df["date"].min(),
        "periode_max": df["date"].max(),
        "formats_source": df["source_format"].value_counts().to_dict()
        if "source_format" in df.columns else "colonne source_format absente",
    }
    print("\n=== 1. Inventaire ===")
    for k, v in report.items():
        print(f"{k}: {v}")
    print("[À COMPLÉTER MANUELLEMENT] Droit d'usage RGPD des 10 ans de données "
          "(base légale du réemploi pour entraîner un modèle — cf doc 02 §8).")
    pd.Series(report).to_csv(out / "1_inventaire.csv")


def step_lien_pcg(df: pd.DataFrame, out: Path):
    print("\n=== 2. Lien libellé bancaire <-> compte PCG (risque n°1) ===")
    total = len(df)
    sans_libelle = df["libelle_brut"].isna() | (df["libelle_brut"].astype(str).str.strip() == "")
    sans_compte = df["compte_pcg"].isna() | (df["compte_pcg"].astype(str).str.strip() == "")
    lien_rompu = sans_libelle | sans_compte
    par_format = None
    if "source_format" in df.columns:
        par_format = df.assign(lien_rompu=lien_rompu).groupby("source_format")["lien_rompu"].mean()
        print("Taux de lien rompu par format source (0 = lien intact) :")
        print(par_format)
    taux = lien_rompu.mean()
    print(f"Taux global de lien rompu : {taux:.2%} sur {total} lignes")
    if taux > 0:
        print("⚠️  Le lien n'est pas garanti sur 100% des 10 ans — vérifier si "
              "concentré sur certains formats/périodes avant de conclure.")
    lien_rompu.to_frame("lien_rompu").to_csv(out / "2_lien_pcg_par_ligne.csv")
    if par_format is not None:
        par_format.to_csv(out / "2_lien_pcg_par_format.csv")


def step_echantillon_labels(df: pd.DataFrame, out: Path, n: int = 500, seed: int = 42):
    print(f"\n=== 3. Échantillon de {n} lignes à faire relire (qualité des labels) ===")
    echantillon = df.sample(n=min(n, len(df)), random_state=seed)
    echantillon.to_csv(out / "3_echantillon_labels_a_relire.csv", index=False)
    print(f"Écrit dans sortie/3_echantillon_labels_a_relire.csv — {len(echantillon)} lignes.")
    print("[À COMPLÉTER MANUELLEMENT] Faire relire par un tiers (comptable) : "
          "% d'accord avec la catégorie historique, en notant qui a fait l'imputation "
          "d'origine si connu (comptable senior / stagiaire / import brut sans revue).")


def step_derive_temporelle(df: pd.DataFrame, out: Path):
    print("\n=== 4. Dérive temporelle ===")
    par_annee = df.groupby(df["date"].dt.year).agg(
        n_lignes=("categorie", "count"),
        n_classes=("categorie", "nunique"),
        n_dossiers=("dossier_id", "nunique"),
    )
    print(par_annee)
    enseignes = df.assign(annee=df["date"].dt.year).groupby("annee")["libelle_brut"].apply(
        lambda s: set(s.astype(str).str.extract(r"^([A-Z ]{3,15})")[0].dropna())
    )
    apparues_disparues = []
    annees = sorted(enseignes.index)
    for a1, a2 in zip(annees, annees[1:]):
        disparues = enseignes[a1] - enseignes[a2]
        nouvelles = enseignes[a2] - enseignes[a1]
        apparues_disparues.append((a1, a2, len(disparues), len(nouvelles)))
    drift_df = pd.DataFrame(apparues_disparues, columns=["annee_a", "annee_b", "n_disparues", "n_nouvelles"])
    print(drift_df)
    par_annee.to_csv(out / "4_derive_par_annee.csv")
    drift_df.to_csv(out / "4_derive_enseignes.csv", index=False)


def step_distribution_classes(df: pd.DataFrame, out: Path, n_min: int = 100):
    print("\n=== 5. Distribution des classes + classes rares ===")
    dist = df["categorie"].value_counts()
    print(dist)
    rares = dist[dist < n_min]
    print(f"\nClasses rares (< {n_min} exemples) : {len(rares)}")
    print(rares)
    print("\n[À COMPLÉTER MANUELLEMENT] Pour chaque classe rare, assigner une politique "
          "(doc 07 §3.4) : exclure de l'auto-validation (enjeu élevé) / regrouper "
          "(enjeu faible) / absente du modèle → routage LLM.")
    dist.to_frame("n_exemples").to_csv(out / "5_distribution_classes.csv")
    rares.to_frame("n_exemples").to_csv(out / "5_classes_rares.csv")


def step_verif_fuite(train_path: str, test_path: str, out: Path):
    print("\n=== 6. Vérification anti-fuite (split par dossier ET période) ===")
    train = pd.read_csv(train_path, parse_dates=["date"])
    test = pd.read_csv(test_path, parse_dates=["date"])
    dossiers_communs = set(train["dossier_id"]) & set(test["dossier_id"])
    print(f"Dossiers présents à la fois dans train et test : {len(dossiers_communs)}")
    if dossiers_communs:
        print("⚠️  FUITE PAR DOSSIER — le split n'isole pas les dossiers, le score est optimiste.")
    train_periods = set(zip(train["date"].dt.year, train["date"].dt.month))
    test_periods = set(zip(test["date"].dt.year, test["date"].dt.month))
    chevauchement = train_periods & test_periods
    print(f"Mois calendaires présents à la fois dans train et test : {len(chevauchement)}")
    if chevauchement:
        print("⚠️  FUITE TEMPORELLE possible — vérifier si c'est un split par dossier "
              "pur (chevauchement de mois acceptable) ou une vraie fuite.")
    pd.Series(sorted(dossiers_communs)).to_csv(out / "6_dossiers_communs.csv", index=False)


def step_precision_classe(model_path: str, test_path: str, out: Path):
    from joblib import load
    from sklearn.metrics import classification_report, confusion_matrix

    print("\n=== 7-8. Précision par classe + matrice de confusion ===")
    model = load(model_path)
    test = pd.read_csv(test_path)
    X = test["libelle_brut"].astype(str) + " " + test["compte_pcg"].astype(str)
    y_true = test["categorie"]
    y_pred = model.predict(X)

    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    report_df = pd.DataFrame(report).T
    print(report_df)

    seuil = 0.95
    classes_sous_seuil = report_df[(report_df.index.isin(y_true.unique())) & (report_df["precision"] < seuil)]
    print(f"\nClasses sous {seuil:.0%} de précision (à exclure de l'auto-validation "
          f"si enjeu élevé — doc 07 §4) :")
    print(classes_sous_seuil[["precision", "recall", "support"]])

    labels = sorted(y_true.unique())
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)
    cm_df.to_csv(out / "7_matrice_confusion.csv")
    report_df.to_csv(out / "7_precision_par_classe.csv")
    print("\n[À COMPLÉTER MANUELLEMENT] Inspecter sortie/7_matrice_confusion.csv à la main : "
          "lister les erreurs graves (ex. charge classée en immobilisation ou l'inverse).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transactions", help="CSV du dataset complet")
    parser.add_argument("--train-set")
    parser.add_argument("--test-set")
    parser.add_argument("--model")
    parser.add_argument("--n-min", type=int, default=100)
    parser.add_argument("--sample-size", type=int, default=500)
    parser.add_argument("--step", default="all", choices=[
        "all", "inventaire", "lien-pcg", "echantillon-labels",
        "derive-temporelle", "distribution-classes", "verif-fuite", "precision-classe",
    ])
    # Permet de remapper les noms de colonnes si l'export diffère du schéma du README.
    parser.add_argument("--col-dossier", default="dossier_id")
    parser.add_argument("--col-date", default="date")
    parser.add_argument("--col-libelle", default="libelle_brut")
    parser.add_argument("--col-montant", default="montant")
    parser.add_argument("--col-compte", default="compte_pcg")
    parser.add_argument("--col-categorie", default="categorie")
    parser.add_argument("--col-source", default="source_format")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    cols = {
        "dossier_id": args.col_dossier, "date": args.col_date,
        "libelle_brut": args.col_libelle, "montant": args.col_montant,
        "compte_pcg": args.col_compte, "categorie": args.col_categorie,
        "source_format": args.col_source,
    }

    df = None
    if args.transactions:
        df = load_transactions(args.transactions, cols)

    steps_needing_df = {"inventaire", "lien-pcg", "echantillon-labels", "derive-temporelle", "distribution-classes"}
    if args.step in steps_needing_df or args.step == "all":
        if df is None:
            sys.exit("--transactions requis pour cette étape")

    if args.step in ("all", "inventaire"):
        step_inventaire(df, OUT_DIR)
    if args.step in ("all", "lien-pcg"):
        step_lien_pcg(df, OUT_DIR)
    if args.step in ("all", "echantillon-labels"):
        step_echantillon_labels(df, OUT_DIR, n=args.sample_size)
    if args.step in ("all", "derive-temporelle"):
        step_derive_temporelle(df, OUT_DIR)
    if args.step in ("all", "distribution-classes"):
        step_distribution_classes(df, OUT_DIR, n_min=args.n_min)
    if args.step in ("all", "verif-fuite"):
        if args.train_set and args.test_set:
            step_verif_fuite(args.train_set, args.test_set, OUT_DIR)
        else:
            print("\n=== 6. Vérification anti-fuite : SKIP (--train-set/--test-set non fournis) ===")
    if args.step in ("all", "precision-classe"):
        if args.model and args.test_set:
            step_precision_classe(args.model, args.test_set, OUT_DIR)
        else:
            print("\n=== 7-8. Précision par classe : SKIP (--model/--test-set non fournis) ===")

    print(f"\nRésultats écrits dans {OUT_DIR}/")


if __name__ == "__main__":
    main()
