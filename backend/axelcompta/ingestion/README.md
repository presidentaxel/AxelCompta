# ingestion/

Orchestration de l'ingestion : sélectionne le(s) `DataProvider` actif(s) pour
un dossier donné (voir [`providers/`](providers/README.md)), déclenche les
appels (sync périodique ou webhook), normalise la sortie brute avant de la
transmettre à `categorize/`.

**Dépendances :** `core`, `tenants`, `packs` (config dossier + pack).

## Contenu prévu

- Normalisation `Decimal` → centimes à l'ingestion.
- Filtrage des transactions `deleted`/`future` côté banque (doc 16 §5).
- File de jobs (Postgres SKIP LOCKED au départ, doc 03 §2).

## Statuts

- **Démo (doc 17 semaine 1)** : normalisation minimale, un seul flux par
  dossier de démo.
- **V1 (doc 12, phase 1)** : orchestration multi-dossiers, retries, monitoring
  des flux par dossier.

## Doc de référence

[doc 04 §5](../../../docs/04-ingestion-donnees.md#5-normalisation--la-sortie-unique-du-module),
[doc 16 §5](../../../docs/16-integration-digifactory.md).
