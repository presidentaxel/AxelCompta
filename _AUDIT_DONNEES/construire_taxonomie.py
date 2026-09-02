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
3. Produit resultats/fec_ml_taxonomie.csv : une ligne par JAMBE nature (pas
   par transaction — une transaction composite comme un settlement
   plateforme en produit plusieurs, voir §2 du code) : dossier_id, piece_ref,
   date, libelle_bancaire, montant, compte_pcg_nature, categorie,
   type_transaction (simple|composite).

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
    "512", "531", "511", "401", "411", "455", "421", "164", "168", "404", "425",
    "445",  # TVA (déductible/collectée/à décaisser) — jamais une catégorie
    "580",  # virements internes (ex. SumUp -> banque) — pas une dépense
    "471",  # compte d'attente/régularisation — trop générique pour trancher
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
#   6257/62560 -> Carrefour, Auchan, McDonalds, KFC, pizza   => repas_et_receptions (RISQUE perso)
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
    ("6257", "repas_et_receptions"),
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
    ("6256", "repas_et_receptions"),
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
    ("120", "operation_capital_hors_perimetre"),   # résultat de l'exercice
    ("129", "operation_capital_hors_perimetre"),   # report à nouveau déficitaire
    ("271", "operation_capital_hors_perimetre"),   # titres de participation

    # Deuxième passe (réduction du bucket non_categorise_a_verifier) :
    ("618", "abonnements_logiciels"),        # Microsoft, Apple
    ("651", "abonnements_logiciels"),        # Spotify
    ("431", "charges_sociales_impots"),      # URSSAF
    ("437", "charges_sociales_impots"),      # autres organismes sociaux (SSI...)
    ("448", "charges_sociales_impots"),      # provisions taxe apprentissage/formation
    ("646", "charges_sociales_impots"),      # cotisations sociales personnelles dirigeant
    ("631", "charges_sociales_impots"),      # taxe d'apprentissage
    ("633", "charges_sociales_impots"),      # formation continue
    ("467", "recettes_plateformes"),         # ⚠️ compte d'attente Uber observé, à confirmer — pas garanti systématique sur tous les dossiers
    ("418", "recettes_plateformes"),         # factures à établir Uber
    ("457", "dividendes_associes"),
    ("613", "loyers_locations"),             # local pro
    ("647", "assurance_personnelle_sante"),  # pharmacie
    ("612", "loa_credit_bail_vehicule"),     # ex. Toyota France Financement
    ("623", "fournitures_administratives"),  # pub/impression, plus large que 6231
    ("602", "fournitures_administratives"),
    ("775", "immobilisation_vehicule"),      # cession véhicule
    ("275", "immobilisation_vehicule"),      # dépôts/cautionnements LOA
    ("201", "honoraires_comptable_juridique"),  # frais de formalités (Entrepreneur.fr)
    ("641", "remuneration_dirigeant"),       # fallback plus large que 6411
    ("604", "sous_traitance_chauffeurs"),
    ("671", "amendes_infractions"),          # fallback plus large que 6712
    ("758", "ecarts_reglement_arrondis"),
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

    # 2. Une ligne de sortie PAR JAMBE "nature" (pas par transaction).
    #
    # Constat en creusant les cas "multi-catégorie" : ce ne sont presque
    # jamais des dépenses réellement ambiguës. Deux cas dominent :
    #  - 68% des cas (1982/2921) : le couple commissions_plateformes +
    #    recettes_plateformes — le settlement Rollee/plateforme a toujours
    #    une jambe commission (622x) ET une jambe recette (706x) sur le
    #    même piece_ref, exactement le schéma du template doc 06 §3.5. Ce
    #    n'est pas une ambiguïté à trancher, c'est une écriture composite
    #    normale — chaque jambe a sa propre catégorie et son propre montant.
    #  - Le reste vient surtout d'écritures "Multiples Comptes ou Produits"
    #    : un lot de règlements/prélèvements groupés sous un même piece_ref
    #    comptable (pas une vraie transaction bancaire unique), avec des
    #    jambes de nature complètement différentes (péage + rémunération +
    #    honoraires + carburant vus dans un seul cas réel). Forcer une seule
    #    catégorie sur le lot était faux ; ventiler jambe par jambe restitue
    #    l'information réelle.
    #
    # Colonne `type_transaction` : "simple" (1 seule jambe nature) vs
    # "composite" (plusieurs) — utile en aval : le couple
    # commissions/recettes partage le MÊME libellé bancaire pour deux
    # catégories différentes, ce qui casserait un entraînement ML texte->
    # catégorie si on ne le filtre pas (voir entrainer_modele_baseline.py).
    stats_categorie = Counter()
    stats_comptes_inconnus = Counter()
    n_composite = 0
    lignes_sortie = []

    for (dossier_id, piece_ref), rows in transactions.items():
        libelles = [r["libelle_brut"] for r in rows]
        date = rows[0]["date"]
        libelle = meilleur_libelle(libelles)
        jambes_nature = []  # (compte_norm, categorie, montant)

        for r in rows:
            compte_norm = normaliser_compte(r["compte_pcg"])
            if est_financier(compte_norm):
                continue
            cat = categorie_pour_compte(compte_norm)
            if cat == CATEGORIE_INCONNUE:
                stats_comptes_inconnus[r["compte_pcg"]] += 1
            jambes_nature.append((compte_norm, cat, r["montant"]))

        if not jambes_nature:
            continue  # transaction 100% financière (ex. juste 512<->531), rien à catégoriser

        categories_distinctes = {cat for _, cat, _ in jambes_nature}
        type_transaction = "composite" if len(categories_distinctes) > 1 else "simple"
        if type_transaction == "composite":
            n_composite += 1

        for i, (compte_norm, cat, montant) in enumerate(jambes_nature):
            stats_categorie[cat] += 1
            lignes_sortie.append({
                "dossier_id": dossier_id,
                "piece_ref": f"{piece_ref}#{i}" if len(jambes_nature) > 1 else piece_ref,
                "date": date,
                "libelle_bancaire": libelle,
                "montant": montant,
                "compte_pcg_nature": compte_norm,
                "categorie": cat,
                "type_transaction": type_transaction,
            })

    with sortie.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "dossier_id", "piece_ref", "date", "libelle_bancaire", "montant",
            "compte_pcg_nature", "categorie", "type_transaction",
        ])
        w.writeheader()
        w.writerows(lignes_sortie)

    total = sum(stats_categorie.values())
    with open(args.rapport, "w", encoding="utf-8") as f:
        f.write(f"Total lignes (une par jambe nature) : {total}\n")
        f.write(f"Dont issues d'une transaction composite (>1 catégorie sur le même piece_ref) : "
                f"{sum(1 for l in lignes_sortie if l['type_transaction'] == 'composite')}\n\n")
        f.write("Répartition par catégorie :\n")
        for cat, n in stats_categorie.most_common():
            f.write(f"  {cat:40s} {n:7d}  ({n/total*100:5.1f}%)\n")
        f.write(f"\nTransactions composites (piece_ref avec >1 catégorie) : {n_composite}\n")
        f.write("\nComptes non mappés (top 30, à ajouter au mapping ou à trancher) :\n")
        for compte, n in stats_comptes_inconnus.most_common(30):
            f.write(f"  {compte:20s} {n:6d}\n")

    print(f"{len(lignes_sortie)} lignes écrites (une par jambe nature) -> {sortie}")
    n_connu = total - stats_categorie[CATEGORIE_INCONNUE]
    print(f"Catégorisées : {n_connu}/{total} ({n_connu/total*100:.1f}%)")
    print(f"Transactions composites : {n_composite}")
    print(f"Rapport détaillé -> {args.rapport}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
