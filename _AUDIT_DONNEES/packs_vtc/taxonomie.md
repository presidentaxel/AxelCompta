# Taxonomie pack VTC — brouillon issu de l'audit du dataset réel

> **Statut : brouillon dérivé de 35 038 transactions réelles (74 dossiers,
> 2017-2025), PAS validé par un expert-comptable ni par Louis.** Chaque
> catégorie est étayée par un échantillon de libellés réels (voir
> `mapping_pcg_categorie.csv`), mais reste une proposition à trancher —
> notamment `repas_et_receptions`, qui recouvre un usage plausiblement
> professionnel (repas hors domicile) mais mélangé avec des achats en
> grande surface plus ambigus — à trancher au cas par cas pendant la
> relecture humaine (voir `../resultats/rapport_audit_dataset.md` §Risques).
>
> Construite pour la démo (doc 17) — 30 catégories (24 en premier passage, 6
> ajoutées en réduisant le bucket non catégorisé le 2026-09-02), pas les
> 40-80 de la taxonomie cible V1 (doc 05 §2). À densifier avec le comptable
> avant production (doc 12 §0.2).
>
> **Qui relit et tranche les cas ambigus : jamais AxeL (doc 02 §2.3, doc 05
> §5)** — l'utilisateur professionnel côté client, ou par délégation le
> chauffeur lui-même pour qualifier une dépense (canal pas encore
> formalisé, doc 05 §5).

| Catégorie | Nature | Volume observé | Sens métier |
|---|---|---:|---|
| `peage_stationnement` | charge | 8 280 (23,6%) | Péages autoroute, parkings (Cofiroute, Sanef, Effia, horodateurs) |
| `carburant` | charge | 6 076 (17,3%) | Essence/gazole (Total, Esso, grandes surfaces avec mention GO) |
| `recettes_plateformes` | produit | 4 467 (12,7%) | Règlements Uber/Bolt/Heetch (virements reçus, factures à établir) |
| `frais_bancaires` | charge | 1 743 (5,0%) | Cotisations carte, commissions bancaires, agios |
| `fournitures_administratives` | charge | 1 189 (3,4%) | Achats divers non stockés — contient des achats à consonance personnelle non isolés, à trancher en relecture (voir rapport) |
| `honoraires_comptable_juridique` | charge | 955 (2,7%) | Expert-comptable, greffe, conseil, formalités |
| `telecommunications` | charge | 950 (2,7%) | SFR, Bouygues, Free Mobile |
| `entretien_reparation_vehicule` | charge | 843 (2,4%) | Norauto, Midas, contrôle technique, lavage |
| `assurance_vehicule` | charge | 705 (2,0%) | MMA, Matmut — assurance auto |
| `a_verifier_location_materiel` | charge | 554 (1,6%) | Prélèvements récurrents (ex. VIAXEL) — nature non confirmée, à trancher |
| `repas_et_receptions` | charge | 516 (1,5%) | Carrefour, Auchan, McDonald's, Quick, Pizza Hut — repas hors domicile plausiblement déductibles (restauration) mêlés à des achats grande surface plus ambigus (courses) — à trancher ligne à ligne |
| `remuneration_dirigeant` | charge | 229 (0,7%) | Virements récurrents identifiés comme rémunération |
| `amendes_infractions` | charge | 178 (0,5%) | amende.gouv — non déductible fiscalement (réintégration IS) |
| `operation_capital_hors_perimetre` | hors ML | 61 (0,2%) | Capital, comptes courants associés, résultat/report à nouveau, titres — pas une dépense |
| `subventions` | produit | 61 (0,2%) | Versements DGFIP hors TVA/IS |
| `immobilisation_vehicule` | investissement | 57 (0,2%) | Achat véhicule, dépôt de garantie LOA, cession, amortissement cumulé |
| `abonnements_logiciels` | charge | 51 (0,1%) | Microsoft, Apple, Spotify |
| `charges_sociales_impots` | charge | 49 (0,1%) | URSSAF, autres organismes sociaux, taxe d'apprentissage/formation |
| `assurance_personnelle_sante` | charge | 25 (0,1%) | Mutuelle santé, pharmacie |
| `interets_emprunts` | charge | 24 (0,1%) | Intérêts (ex. ADIE) |
| `commissions_plateformes` | charge | 22 (0,1%) | Commission Uber/Bolt (hors recette nette Rollee) |
| `visite_medicale_vtc` | charge | 19 (0,1%) | Médecine du travail / visite d'aptitude |
| `sous_traitance_chauffeurs` | charge | 16 (0,0%) | Sous-traitance à d'autres chauffeurs |
| `etat_taxes_diverses` | charge | 16 (0,0%) | Comptes d'État divers non affectés |
| `dividendes_associes` | hors ML | 11 (0,0%) | Dividendes à payer aux associés |
| `loa_credit_bail_vehicule` | charge | 10 (0,0%) | Redevances crédit-bail (ex. Toyota France Financement) |
| `loyers_locations` | charge | 8 (0,0%) | Location de local professionnel |
| `ecarts_reglement_arrondis` | technique | 4 (0,0%) | Écarts d'arrondi TVA — non matériel, gardé pour traçabilité |
| `dotations_amortissements` | hors ML | — | Généré automatiquement à la clôture (doc 06 §3.3), jamais dans un flux bancaire — exclu du jeu d'entraînement ML |

**Buckets techniques (pas des catégories métier) :**
- `multi_categorie_a_ventiler` (2 900 transactions, 8,3%) : plusieurs comptes de
  nature différents sur la même transaction (ex. un paiement carte ventilé
  entre deux charges). Légitime, mais nécessite une règle de ventilation ou
  une revue au cas par cas — pas une erreur de mapping.
- `non_categorise_a_verifier` (5 124 transactions, 14,6%) : compte PCG pas
  encore mappé (longue traîne de comptes à faible volume, voir
  `mapping_pcg_categorie.csv` §comptes non mappés).
