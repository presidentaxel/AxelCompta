"""Dérive temporelle du dataset (doc 12 §0.2 — item roadmap non coché,
équivalent de l'étape 4 d'audit_dataset.py, adapté au schéma par jambe).

Deux questions :
1. Le volume/mix de catégories change-t-il fortement dans le temps ? Si oui,
   un split train/test qui ignore la période (même avec un split propre par
   dossier) resterait optimiste sur les années récentes (doc 07 §2.2 exige
   un split par dossier ET par période).
2. Le format des comptes PCG (bourrage de zéros, voir rapport_audit_dataset.md
   §5) dérive-t-il avec l'année ? Utile pour savoir si la normalisation
   actuelle (4 chiffres significatifs) tiendra sur les imports futurs.

Usage:
    python analyser_derive_temporelle.py
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

ENTREE = Path("resultats/fec_ml_taxonomie.csv")
BRUT = Path("sortie/transactions.csv")
SORTIE = Path("resultats/rapport_derive_temporelle.txt")


def annee(date_str: str) -> str:
    return date_str[:4] if date_str else "?"


def main() -> None:
    par_annee_categorie = defaultdict(Counter)
    par_annee_total = Counter()
    with ENTREE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a = annee(row["date"])
            par_annee_categorie[a][row["categorie"]] += 1
            par_annee_total[a] += 1

    # longueur brute des comptes PCG par année (indicateur de dérive de format)
    longueur_compte_par_annee = defaultdict(list)
    with BRUT.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a = annee(row["date"])
            longueur_compte_par_annee[a].append(len(row["compte_pcg"].strip()))

    annees = sorted(a for a in par_annee_total if a != "?")

    with SORTIE.open("w", encoding="utf-8") as f:
        f.write("Volume de lignes par année :\n")
        for a in annees:
            f.write(f"  {a}: {par_annee_total[a]:6d}\n")

        f.write("\nPart des 5 catégories dominantes par année (%) :\n")
        top5_global = [c for c, _ in Counter(
            {c: sum(par_annee_categorie[a][c] for a in annees) for c in
             set().union(*[set(par_annee_categorie[a]) for a in annees])}
        ).most_common(5)]
        f.write(f"  Catégories suivies : {top5_global}\n")
        f.write(f"  {'année':>6} " + " ".join(f"{c[:14]:>15}" for c in top5_global) + "\n")
        for a in annees:
            total = par_annee_total[a] or 1
            parts = [f"{par_annee_categorie[a][c]/total*100:14.1f}%" for c in top5_global]
            f.write(f"  {a:>6} " + " ".join(parts) + "\n")

        f.write("\nLongueur moyenne du compte_pcg brut par année "
                "(dérive de format de bourrage) :\n")
        for a in annees:
            lens = longueur_compte_par_annee[a]
            moy = sum(lens) / len(lens) if lens else 0
            f.write(f"  {a}: moyenne={moy:.1f} caractères, "
                    f"formats distincts={len(set(lens))}\n")

        f.write("\nTaux non_categorise_a_verifier par année (%) :\n")
        for a in annees:
            total = par_annee_total[a] or 1
            n_inc = par_annee_categorie[a]["non_categorise_a_verifier"]
            f.write(f"  {a}: {n_inc}/{total} ({n_inc/total*100:.2f}%)\n")

    print(f"Rapport -> {SORTIE}")
    print(f"Années couvertes : {annees[0]}–{annees[-1]} ({len(annees)} années)")


if __name__ == "__main__":
    main()
