# ingestion/

Orchestration de l'ingestion : sélectionne le(s) `DataProvider` actif(s) pour
un dossier donné (voir [`providers/`](providers/README.md)), déclenche les
appels (sync périodique ou webhook), normalise la sortie brute avant de la
transmettre à `categorize/`.

**Dépendances :** `core`, `tenants`, `packs` (config dossier + pack), `ledger`
(types uniquement, pour construire les `Ecriture` de settlement — `ledger`
ne dépend jamais d'`ingestion` en retour, règle absolue doc 03 §3).

## Fichiers

- `providers/` — pattern `DataProvider` (voir son propre README).
- `reconciliation.py` — `reconcilier()` (doc 13 §4.2, **fait semaine 2**) :
  montant ±1 centime, fenêtre de date [-3j, +5j] autour du `payout_date`,
  libellé contenant le nom de la plateforme. Trois états rapportés (doc 13
  §4.3, réduit) : `RECONCILIE`, `EN_ATTENTE_BANQUE`, `REVUE_MANUELLE` — pas
  de file de revue construite (doc 17 §3), l'état est juste rapporté.
- `ecritures_settlement.py` — `construire_ecriture_settlement()` (doc 13 §5,
  **fait semaine 2**) : ventilation TVA réelle depuis un settlement
  réconcilié, templates de données par régime de commission (`france_20`
  Uber, `autoliquidation_ue` Bolt), taux de TVA recettes figé à 10% assujetti
  (profil unique démo, doc 17 §3).

## Contenu prévu (au-delà de la démo)

- Normalisation `Decimal` → centimes à l'ingestion (fait dans les providers
  eux-mêmes pour la démo — semaine 2 : à centraliser ici en V1).
- Filtrage des transactions `deleted`/`future` côté banque (doc 16 §5, fait
  pour `DigifactoryProvider`).
- File de jobs (Postgres SKIP LOCKED au départ, doc 03 §2).

## Statuts

- **Démo (doc 17 semaines 0-2, fait)** : réconciliation réelle + génération
  d'écriture avec ventilation TVA réelle (golden test doc 13 §5.3 reproduit
  exactement, cas Bolt autoliquidation testé séparément).
- **V1 (doc 12, phase 1)** : orchestration multi-dossiers, retries, monitoring
  des flux par dossier, normalisation centralisée.

## Doc de référence

[doc 04 §5](../../../docs/04-ingestion-donnees.md#5-normalisation--la-sortie-unique-du-module),
[doc 16 §5](../../../docs/16-integration-digifactory.md).
