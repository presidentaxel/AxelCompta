# ingestion/

Orchestration de l'ingestion : sélectionne le(s) `DataProvider` actif(s) pour
un dossier donné (voir [`providers/`](providers/README.md)), déclenche les
appels (sync périodique ou webhook), normalise la sortie brute avant de la
transmettre à `categorize/`.

**Dépendances :** `core`, `tenants`, `packs` (config dossier + pack).

## Fichiers

- `providers/` — pattern `DataProvider` (voir son propre README).
- `reconciliation.py` — matching `PlatformSettlement` ↔ `NormalizedTransaction`
  (doc 13 §2.1, §4). `reconcilier_bouchon` (doc 17 semaine 0, fait) : égalité
  exacte de montant, un seul candidat accepté. L'algorithme réel (fenêtre de
  date, heuristique de libellé, tolérance 1 centime, doc 13 §4.2) est prévu
  semaine 2.

## Contenu prévu (au-delà de la démo)

- Normalisation `Decimal` → centimes à l'ingestion.
- Filtrage des transactions `deleted`/`future` côté banque (doc 16 §5).
- File de jobs (Postgres SKIP LOCKED au départ, doc 03 §2).

## Statuts

- **Démo (doc 17 semaine 0, fait)** : `reconcilier_bouchon` tourne contre les
  fixtures. **Semaine 1-2 (à faire)** : normalisation réelle, algorithme de
  matching complet (doc 13 §4.2).
- **V1 (doc 12, phase 1)** : orchestration multi-dossiers, retries, monitoring
  des flux par dossier.

## Doc de référence

[doc 04 §5](../../../docs/04-ingestion-donnees.md#5-normalisation--la-sortie-unique-du-module),
[doc 16 §5](../../../docs/16-integration-digifactory.md).
