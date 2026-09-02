"""Construit la taxonomie du pack VTC à partir du dataset FEC réel audité.

Étape suivante annoncée dans extraire_fec.py : la table de correspondance
compte PCG -> catégorie métier. Ce script :

1. Regroupe les lignes d'une même transaction par (dossier_id, piece_ref) —
   une écriture FEC "carburant" comprend en général 3 jambes (charge 606x,
   TVA déductible 4456x, banque 512x). Le compte 512 ne porte aucune
   information de catégorie : c'est le même compte quelle que soit la
   dépense. La catégorie vient de la jambe "nature" (6xxx/7xxx).
2. Applique une table de mapping préfixe(compte PCG normalisé) -> catégorie,
   construite à partir d'un échantillon réel de libellés par compte (voir
   rapport_audit_dataset.md pour le détail comte par compte).
3. Produit resultats/fec_ml_taxonomie.csv : une ligne par transaction
   (dossier_id, piece_ref, date, libelle_bancaire, montant, compte_pcg_nature,
   categorie, confiance_mapping).

**Statut du mapping : brouillon dérivé des comptes PCG + échantillons de
libellés, PAS validé par un expert-comptable.** Voir rapport_audit_dataset.md
§"Risques et angles morts" pour les comptes ambigus (frais de bouche,
fournitures mêlant achats pro et perso) qui nécessitent un vrai arbitrage
humain, pas une règle de préfixe.

Usage:
    python construire_taxonomie.py --entree sortie/transactions.csv \
        --sortie resultats/fec_ml_taxonomie.csv
"""
import argparse
import csv
import sys
from collections import defaultdict, Counter
from pathlib import Path

# -----------------------------------------------------------------------------
# Comptes "financiers" : jamais une catégorie en soi, toujours la contrepartie
# d'une jambe "nature". On ignore ces comptes pour déterminer la catégorie
# d'une transaction, mais leur libellé sert souvent de meilleur libellé
# bancaire brut (c'est la jambe qui vient du relevé).
# -----------------------------------------------------------------------------
PREFIXES_FINANCIERS = (
    "512", "531", "511", "401", "411", "4551", "421", "164", "168", "404", "425",
    "445",  # TVA (déductible/collectée/à décaisser) — jamais une catégorie
)

# -----------------------------------------------------------------------------
# Mapping compte PCG (préfixe, sur la forme normalisée sans zéros de
# bourrage) -> catégorie du pack VTC. Construit à partir d'un échantillon de
# libellés réels par compte (voir rapport_audit_dataset.md). Trié du plus
# spécifique au moins spécifique ; le premier préfixe qui matche gagne.
#
# Preuves (extrait, compte -> échantillon de libellés observés) :
#   6061/60614 -> Total, Esso, E Leclerc ...GO (gazole)      => carburant
#   6155/61550 -> Norauto, Midas, contrôle technique, lavage => entretien
#   6251/62510 -> Cofiroute, Sanef, Effia, horodateur/parking=> péage_stationnement
#   6161/6162/6450/6160 -> MMA, Matmut, mutuelle             => assurance
#   622x       -> commissions plateformes (Uber/Bolt)        => commissions_plateformes
#   6226/6227/62265 -> Entrepreneur.fr, Imprimerie, "conseil"=> honoraires
#   626x       -> SFR, Bouygues, Free Mobile                 => telecommunications
#   627x/6278  -> "cotis" carte, commissions bancaires, CIC  => frais_bancaires
#   606x (hors 6061) -> Vistaprint, Boulanger, Fnac, Amazon  => fournitures_administratives
#   6257/62560 -> Carrefour, Auchan, McDonalds, KFC, pizza   => frais_bouche_a_verifier (RISQUE perso)
#   6712       -> WEB AMENDE.GOUV                            => amendes
#   611x       -> "CHAUFF sous-traitance"                    => sous_traitance_chauffeurs
#   641x       -> "VIR EUROPEEN" récurrents                  => remuneration_dirigeant
#   645x/635x  -> URSSAF, DGFIP                               => charges_sociales_impots
#   68x/695x   -> "Ecriture Comptable - Amortissements"/OD   => dotations_amortissements (hors ML, généré à la clôture)
#   706x       -> VIR RECU (règlements plateformes)          => recettes_plateformes
#   741x       -> DGFIP SCBCM MINEFI                         => subventions
# -----------------------------------------------------------------------------
MAPPING_PREFIXES = [
    ("60611", "carburant"),
    ("6061", "carburant"),
    ("60614", "carburant"),
    ("6155", "entretien_reparation_vehicule"),
    ("6135", "a_verifier_location_materiel"),  # VIAXEL récurrent, nature non confirmée
    ("6251", "peage_stationnement"),
    ("6162", "assurance_vehicule"),
    ("6161", "assurance_vehicule"),
    ("6160", "assurance_vehicule"),
    ("6450", "assurance_personnelle_sante"),
    ("6475", "visite_medicale_vtc"),
    ("622", "commissions_plateformes"),
    ("6226", "honoraires_comptable_juridique"),
    ("6227", "honoraires_comptable_juridique"),
    ("626", "telecommunications"),
    ("627", "frais_bancaires"),
    ("6257", "frais_bouche_a_verifier"),
    ("6060", "fournitures_administratives"),
    ("6063", "fournitures_administratives"),
    ("6064", "fournitures_administratives"),
    ("6068", "fournitures_administratives"),
    ("6580", "fournitures_administratives"),
    ("6712", "amendes_infractions"),
    ("611", "sous_traitance_chauffeurs"),
    ("6411", "remuneration_dirigeant"),
    ("645", "charges_sociales_impots"),
    ("635", "charges_sociales_impots"),
    ("6231", "fournitures_administratives"),  # pub/impression
    ("681", "dotations_amortissements"),
    ("695", "dotations_amortissements"),
    ("6951", "dotations_amortissements"),
    ("706", "recettes_plateformes"),
    ("741", "subventions"),
    ("6256", "frais_bouche_a_verifier"),
    ("606", "fournitures_administratives"),   # filet, compte générique non subdivisé
    ("658", "fournitures_administratives"),   # filet, idem
    ("661", "interets_emprunts"),
    ("218", "immobilisation_vehicule"),
    ("2751", "immobilisation_vehicule"),      # dépôt de garantie LOA
    ("2818", "immobilisation_vehicule"),      # amortissement cumulé véhicule
    ("444", "etat_taxes_diverses"),
    ("101", "operation_capital_hors_perimetre"),
    ("1100", "operation_capital_hors_perimetre"),
    ("1190", "operation_capital_hors_perimetre"),
]

# Comptes explicitement laissés "à vérifier" faute de preuve suffisante dans
# l'échantillon (peu d'occurrences, libellé trop générique). Ne pas deviner.
CATEGORIE_INCONNUE = "non_categorise_a_verifier"


def normaliser_compte(compte: str) -> str:
    """"6257000000", "6257000", "62570000" -> "6257" (préfixe significatif).

    Les comptes du dataset ne sont pas bourrés de zéros de façon homogène
    (dossiers/années différents) : ceci est un vrai constat d'audit, voir
    rapport_audit_dataset.md.
    """
    c = compte.strip().lstrip("0") or "0"
    # Coupe les zéros de bourrage à droite en gardant au moins 4 chiffres
    # significatifs (les comptes du pack VTC se distinguent au 4e chiffre :
    # 6061 carburant vs 6063 entretien vs 6064 fournitures). En dessous de 4,
    # on ne peut plus trancher entre un compte 3 chiffres réel (706, 622) et
    # un compte 4 chiffres tout en zéros (6580) : on s'arrête à 4 et on
    # laisse le matching par préfixe (startswith) absorber les comptes
    # réellement courts.
    while len(c) > 4 and c.endswith("0") and not c[:3].isalpha():
        c = c[:-1]
    return c


def categorie_pour_compte(compte_norm: str) -> str:
    for prefix, categorie in sorted(MAPPING_PREFIXES, key=lambda x: -len(x[0])):
        if compte_norm.startswith(prefix):
            return categorie
    return CATEGORIE_INCONNUE


def est_financier(compte_norm: str) -> bool:
    return compte_norm.startswith(PREFIXES_FINANCIERS)


def meilleur_libelle(libelles: list[str]) -> str:
    """Heuristique : le libellé le plus long/informatif parmi les jambes."""
    return max(libelles, key=lambda s: len(s.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entree", default="sortie/transactions.csv")
    parser.add_argument("--sortie", default="resultats/fec_ml_taxonomie.csv")
    parser.add_argument("--rapport", default="resultats/rapport_taxonomie.txt")
    args = parser.parse_args()

    entree = Path(args.entree)
    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)

    # 1. Regroupe par transaction (dossier_id, piece_ref)
    transactions = defaultdict(list)  # (dossier_id, piece_ref) -> [rows]
    with entree.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            transactions[(row["dossier_id"], row["piece_ref"])].append(row)

    stats_categorie = Counter()
    stats_comptes_inconnus = Counter()
    n_multi_categorie = 0
    lignes_sortie = []

    for (dossier_id, piece_ref), rows in transactions.items():
        libelles = [r["libelle_brut"] for r in rows]
        date = rows[0]["date"]
        montant_bancaire = None
        categories_trouvees = set()
        compte_nature_retenu = None

        for r in rows:
            compte_norm = normaliser_compte(r["compte_pcg"])
            if est_financier(compte_norm):
                if compte_norm.startswith("512") or compte_norm.startswith("531"):
                    montant_bancaire = r["montant"]
                continue
            cat = categorie_pour_compte(compte_norm)
            categories_trouvees.add(cat)
            if cat != CATEGORIE_INCONNUE:
                compte_nature_retenu = compte_norm
            else:
                stats_comptes_inconnus[r["compte_pcg"]] += 1

        categories_trouvees.discard(CATEGORIE_INCONNUE) or None
        if len(categories_trouvees) == 0:
            categorie = CATEGORIE_INCONNUE
        elif len(categories_trouvees) == 1:
            categorie = next(iter(categories_trouvees))
        else:
            # plusieurs jambes "nature" différentes sur la même transaction
            # (ex : ventilation carburant + péage sur un même paiement CB) :
            # on ne force pas une seule catégorie, on le signale.
            categorie = "multi_categorie_a_ventiler"
            n_multi_categorie += 1

        stats_categorie[categorie] += 1
        lignes_sortie.append({
            "dossier_id": dossier_id,
            "piece_ref": piece_ref,
            "date": date,
            "libelle_bancaire": meilleur_libelle(libelles),
            "montant": montant_bancaire or "",
            "compte_pcg_nature": compte_nature_retenu or "",
            "categorie": categorie,
        })

    with sortie.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "dossier_id", "piece_ref", "date", "libelle_bancaire", "montant",
            "compte_pcg_nature", "categorie",
        ])
        w.writeheader()
        w.writerows(lignes_sortie)

    total = sum(stats_categorie.values())
    with open(args.rapport, "w", encoding="utf-8") as f:
        f.write(f"Total transactions : {total}\n\n")
        f.write("Répartition par catégorie :\n")
        for cat, n in stats_categorie.most_common():
            f.write(f"  {cat:40s} {n:7d}  ({n/total*100:5.1f}%)\n")
        f.write(f"\nTransactions multi-catégorie (à ventiler) : {n_multi_categorie}\n")
        f.write("\nComptes non mappés (top 30, à ajouter au mapping ou à trancher) :\n")
        for compte, n in stats_comptes_inconnus.most_common(30):
            f.write(f"  {compte:20s} {n:6d}\n")

    print(f"{len(lignes_sortie)} transactions écrites -> {sortie}")
    n_connu = total - stats_categorie[CATEGORIE_INCONNUE] - stats_categorie.get("multi_categorie_a_ventiler", 0)
    print(f"Catégorisées : {n_connu}/{total} ({n_connu/total*100:.1f}%)")
    print(f"Rapport détaillé -> {args.rapport}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
