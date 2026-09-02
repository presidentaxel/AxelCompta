# Taxonomie pack VTC — brouillon issu de l'audit du dataset réel

> **Statut : brouillon dérivé de 35 038 transactions réelles (74 dossiers,
> 2017-2025), PAS validé par un expert-comptable ni par Louis.** Chaque
> catégorie est étayée par un échantillon de libellés réels (voir
> `mapping_pcg_categorie.csv`), mais reste une proposition à trancher —
> notamment les deux catégories marquées ⚠️ *à vérifier*, qui recouvrent un
> vrai risque d'usage personnel non retraité dans l'historique (voir
> `../resultats/rapport_audit_dataset.md` §Risques).
>
> Construite pour la démo (doc 17) — 24 catégories, pas les 40-80 de la
> taxonomie cible V1 (doc 05 §2). À densifier avec le comptable avant
> production (doc 12 §0.2).

| Catégorie | Nature | Volume observé | Sens métier |
|---|---|---:|---|
| `peage_stationnement` | charge | 8 284 (23,6%) | Péages autoroute, parkings (Cofiroute, Sanef, Effia, horodateurs) |
| `carburant` | charge | 6 080 (17,4%) | Essence/gazole (Total, Esso, grandes surfaces avec mention GO) |
| `recettes_plateformes` | produit | 4 469 (12,8%) | Règlements Uber/Bolt/Heetch (virements reçus) |
| `frais_bancaires` | charge | 1 743 (5,0%) | Cotisations carte, commissions bancaires, agios |
| `fournitures_administratives` | charge | 1 181 (3,4%) | Achats divers non stockés — ⚠️ **contient des achats à consonance personnelle non isolés** (voir rapport) |
| `honoraires_comptable_juridique` | charge | 953 (2,7%) | Expert-comptable, greffe, conseil |
| `telecommunications` | charge | 951 (2,7%) | SFR, Bouygues, Free Mobile |
| `entretien_reparation_vehicule` | charge | 843 (2,4%) | Norauto, Midas, contrôle technique, lavage |
| `assurance_vehicule` | charge | 705 (2,0%) | MMA, Matmut — assurance auto |
| `a_verifier_location_materiel` | charge | 554 (1,6%) | Prélèvements récurrents (ex. VIAXEL) — nature non confirmée, à trancher |
| `frais_bouche_a_verifier` | charge | 519 (1,5%) | ⚠️ Carrefour, Auchan, McDonald's, Quick, Pizza Hut — **usage personnel probable, jamais retraité en 455/108** |
| `remuneration_dirigeant` | charge | 230 (0,7%) | Virements récurrents identifiés comme rémunération |
| `amendes_infractions` | charge | 177 (0,5%) | amende.gouv — non déductible fiscalement (réintégration IS) |
| `subventions` | produit | 61 (0,2%) | Versements DGFIP hors TVA/IS |
| `operation_capital_hors_perimetre` | hors ML | 59 (0,2%) | Mouvements de capital/compte courant associé — pas une dépense |
| `immobilisation_vehicule` | investissement | 51 (0,1%) | Achat véhicule, dépôt de garantie LOA, amortissement cumulé |
| `charges_sociales_impots` | charge | 43 (0,1%) | URSSAF, DGFIP |
| `interets_emprunts` | charge | 24 (0,1%) | Intérêts (ex. ADIE) |
| `commissions_plateformes` | charge | 22 (0,1%) | Commission Uber/Bolt (hors recette nette Rollee) |
| `visite_medicale_vtc` | charge | 19 (0,1%) | Médecine du travail / visite d'aptitude |
| `etat_taxes_diverses` | charge | 17 (0,0%) | Comptes d'État divers non affectés |
| `sous_traitance_chauffeurs` | charge | 15 (0,0%) | Sous-traitance à d'autres chauffeurs |
| `assurance_personnelle_sante` | charge | 14 (0,0%) | Mutuelle santé du dirigeant |
| `dotations_amortissements` | hors ML | — | Généré automatiquement à la clôture (doc 06 §3.3), jamais dans un flux bancaire — exclu du jeu d'entraînement ML |

**Buckets techniques (pas des catégories métier) :**
- `multi_categorie_a_ventiler` (2 900 transactions, 8,3%) : plusieurs comptes de
  nature différents sur la même transaction (ex. un paiement carte ventilé
  entre deux charges). Légitime, mais nécessite une règle de ventilation ou
  une revue au cas par cas — pas une erreur de mapping.
- `non_categorise_a_verifier` (5 124 transactions, 14,6%) : compte PCG pas
  encore mappé (longue traîne de comptes à faible volume, voir
  `mapping_pcg_categorie.csv` §comptes non mappés).
