# Taxonomie pack VTC — brouillon issu de l'audit du dataset réel

> **Statut : brouillon dérivé de 36 152 lignes réelles (74 dossiers,
> 2017-2025, une ligne par jambe comptable « nature »), PAS validé par un
> expert-comptable ni par Louis.** Chaque catégorie est étayée par un
> échantillon de libellés réels (voir `mapping_pcg_categorie.csv`), mais
> reste une proposition à trancher — notamment `repas_et_receptions`, qui
> recouvre un usage plausiblement professionnel (repas hors domicile) mais
> mélangé avec des achats en grande surface plus ambigus — à trancher au cas
> par cas pendant la relecture humaine (voir
> `../resultats/rapport_audit_dataset.md`).
>
> Construite pour la démo (doc 17) — 30 catégories, pas les 40-80 de la
> taxonomie cible V1 (doc 05 §2). À densifier avec le comptable avant
> production (doc 12 §0.2).
>
> **Une ligne = une jambe « nature », pas une transaction bancaire.** Une
> transaction composite (ex. un settlement plateforme = commission +
> recette sur le même `piece_ref`) produit plusieurs lignes, une par
> catégorie réelle — colonne `type_transaction` (`simple`/`composite`) dans
> `../resultats/fec_ml_taxonomie.csv`. Voir rapport d'audit §3bis.
>
> **Qui relit et tranche les cas ambigus : jamais AxeL (doc 02 §2.3, doc 05
> §5)** — l'utilisateur professionnel côté client, ou par délégation le
> chauffeur lui-même pour qualifier une dépense (canal pas encore
> formalisé, doc 05 §5).

| Catégorie | Nature | Volume observé | Sens métier |
|---|---|---:|---|
| `peage_stationnement` | charge | 8 982 (24,8%) | Péages autoroute, parkings (Cofiroute, Sanef, Effia, horodateurs) |
| `recettes_plateformes` | produit | 7 004 (19,4%) | Règlements Uber/Bolt/Heetch (virements reçus, factures à établir) |
| `carburant` | charge | 6 709 (18,6%) | Essence/gazole (Total, Esso, grandes surfaces avec mention GO) |
| `frais_bancaires` | charge | 2 344 (6,5%) | Cotisations carte, commissions bancaires, agios |
| `commissions_plateformes` | charge | 2 067 (5,7%) | Commission Uber/Bolt — quasi toujours la jambe jumelle d'une `recettes_plateformes` composite (voir §3bis du rapport) |
| `fournitures_administratives` | charge | 1 425 (3,9%) | Achats divers non stockés — contient des achats à consonance personnelle non isolés, à trancher en relecture |
| `honoraires_comptable_juridique` | charge | 1 282 (3,5%) | Expert-comptable, greffe, conseil, formalités |
| `telecommunications` | charge | 1 249 (3,5%) | SFR, Bouygues, Free Mobile |
| `entretien_reparation_vehicule` | charge | 1 087 (3,0%) | Norauto, Midas, contrôle technique, lavage |
| `assurance_vehicule` | charge | 967 (2,7%) | MMA, Matmut — assurance auto |
| `repas_et_receptions` | charge | 688 (1,9%) | Carrefour, Auchan, McDonald's, Quick, Pizza Hut — repas hors domicile plausiblement déductibles (restauration) mêlés à des achats grande surface plus ambigus (courses) — à trancher ligne à ligne |
| `a_verifier_location_materiel` | charge | 686 (1,9%) | Prélèvements récurrents (ex. VIAXEL) — nature non confirmée, à trancher |
| `remuneration_dirigeant` | charge | 282 (0,8%) | Virements récurrents identifiés comme rémunération — libellé peu informatif, voir rapport §6 |
| `immobilisation_vehicule` | investissement | 263 (0,7%) | Achat véhicule, dépôt de garantie LOA, cession, amortissement cumulé |
| `amendes_infractions` | charge | 257 (0,7%) | amende.gouv — non déductible fiscalement (réintégration IS) |
| `operation_capital_hors_perimetre` | hors ML | 186 (0,5%) | Capital, comptes courants associés, résultat/report à nouveau, titres — pas une dépense |
| `charges_sociales_impots` | charge | 176 (0,5%) | URSSAF, autres organismes sociaux, taxe d'apprentissage/formation |
| `abonnements_logiciels` | charge | 83 (0,2%) | Microsoft, Apple, Spotify |
| `dotations_amortissements` | hors ML | 67 (0,2%) | Généré automatiquement à la clôture (doc 06 §3.3), jamais dans un flux bancaire — exclu du jeu d'entraînement ML |
| `subventions` | produit | 66 (0,2%) | Versements DGFIP hors TVA/IS |
| `etat_taxes_diverses` | charge | 61 (0,2%) | Comptes d'État divers non affectés |
| `interets_emprunts` | charge | 53 (0,1%) | Intérêts (ex. ADIE) |
| `sous_traitance_chauffeurs` | charge | 47 (0,1%) | Sous-traitance à d'autres chauffeurs |
| `assurance_personnelle_sante` | charge | 26 (0,1%) | Mutuelle santé, pharmacie |
| `visite_medicale_vtc` | charge | 25 (0,1%) | Médecine du travail / visite d'aptitude |
| `dividendes_associes` | hors ML | 15 (0,0%) | Dividendes à payer aux associés |
| `loyers_locations` | charge | 12 (0,0%) | Location de local professionnel |
| `loa_credit_bail_vehicule` | charge | 10 (0,0%) | Redevances crédit-bail (ex. Toyota France Financement) |
| `ecarts_reglement_arrondis` | technique | 6 (0,0%) | Écarts d'arrondi TVA — non matériel, gardé pour traçabilité |

**Bucket technique résiduel :** `non_categorise_a_verifier` (27 lignes, 0,1%)
— longue traîne de comptes à 1-2 occurrences, voir
`../resultats/rapport_taxonomie.txt` §comptes non mappés. Rendement
décroissant, laissé tel quel.
