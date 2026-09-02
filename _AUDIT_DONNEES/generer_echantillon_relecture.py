"""Génère les 500 lignes à relire à la main = premier jeu de test gelé
(doc 12 §0.2, dernier item non coché de la phase 0 sur les données).

Échantillonnage stratifié : proportionnel par catégorie, avec un plancher
par catégorie pour que les classes rares et les buckets à risque
(frais_bouche_a_verifier, non_categorise_a_verifier, multi_categorie_a_ventiler)
soient représentés — ce sont eux qui ont le plus besoin d'un œil humain.
Dispersé sur plusieurs dossiers pour ne pas biaiser sur les habitudes de
saisie d'un seul comptable.

**La colonne `categorie_proposee` est le brouillon algorithmique (compte PCG
+ règles), PAS une vérité terrain.** La colonne `categorie_validee` est à
remplir à la main — c'est elle qui devient le jeu de test gelé une fois
complétée. Tant qu'elle n'est pas remplie, aucune mesure de précision du
futur modèle n'est fiable.

Usage:
    python generer_echantillon_relecture.py
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

ENTREE = Path("resultats/fec_ml_taxonomie.csv")
SORTIE = Path("resultats/echantillon_500_a_relire.csv")
TAILLE_CIBLE = 500
PLANCHER_PAR_CATEGORIE = 8
SEED = 20260902  # figé pour reproductibilité


def main() -> None:
    random.seed(SEED)
    par_categorie = defaultdict(list)
    with ENTREE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            par_categorie[row["categorie"]].append(row)

    total = sum(len(v) for v in par_categorie.values())
    echantillon = []

    # 1. plancher par catégorie (protège les classes rares)
    for cat, rows in par_categorie.items():
        random.shuffle(rows)
        n = min(PLANCHER_PAR_CATEGORIE, len(rows))
        echantillon.extend(rows[:n])
        par_categorie[cat] = rows[n:]  # retire ce qui a été pris

    # 2. complète proportionnellement jusqu'à TAILLE_CIBLE
    restant = TAILLE_CIBLE - len(echantillon)
    if restant > 0:
        pool = [r for rows in par_categorie.values() for r in rows]
        random.shuffle(pool)
        echantillon.extend(pool[:restant])

    random.shuffle(echantillon)

    with SORTIE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "dossier_id", "date", "libelle_bancaire", "montant",
            "compte_pcg_nature", "categorie_proposee", "categorie_validee",
            "commentaire",
        ])
        for r in echantillon:
            w.writerow([
                r["dossier_id"], r["date"], r["libelle_bancaire"],
                r["montant"], r["compte_pcg_nature"], r["categorie"],
                "", "",
            ])

    n_dossiers = len({r["dossier_id"] for r in echantillon})
    print(f"{len(echantillon)} lignes échantillonnées sur {total}, "
          f"{n_dossiers} dossiers distincts -> {SORTIE}")


if __name__ == "__main__":
    main()
