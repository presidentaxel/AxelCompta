# workflow/

Validation, circuit de relecture humaine, signature électronique. C'est le
seul module autorisé à transformer une `ProposedEntry` (sortie de
`categorize/`) en écriture réelle via `ledger/`.

**Dépendances :** `core`, `categorize`, `ingestion` (types transaction),
`ledger`.

## Fichiers

- `auto_accept.py` — `construire_ecriture_categorisee()` (**fait, semaine 2**) :
  stand-in minimal, accepte toute `ProposedEntry` sans validation humaine et
  construit une écriture 512/compte-catégorie (pas de ventilation TVA — ça,
  c'est réservé au settlement plateforme, `ingestion/ecritures_settlement.py`).
  **Pas l'architecture cible** : la vraie file de revue (doc 05 §5) reste à
  construire, ceci ne fait que satisfaire la règle de dépendance (« seul
  workflow transforme une ProposedEntry en écriture ») pour que la démo
  tourne sans revue humaine.
- `decisions.py` — `DecisionHumaine`, `AnnotationDev`, `DecisionRepository`
  (**fait, 2026-09-07, doc 17 §9 bloc A**) : modèle de la vraie décision
  humaine (immuable, doc 05 §5 précisé) et de l'annotation dev séparée pour
  le réentraînement — ne remplace pas `auto_accept.py`, prépare le
  branchement de l'écran de revue (bloc C) par-dessus.
- `decisions_memory.py` — `InMemoryDecisionRepository` (**fait,
  2026-09-07**) : implémentation en mémoire, pour les tests unitaires
  rapides — comme `ledger/memory.py` pour le ledger.
- `orm.py` / `decisions_postgres.py` — `PostgresDecisionRepository`
  (**fait, 2026-09-07**) : la vraie persistance (doc 17 §9 bloc A). Deux
  tables (`decisions_humaines`, `annotations_dev`), append-only, **sans
  FK** vers `dossiers`/`ecritures` — ces deux-là restent recalculés à la
  volée pour la démo (`demo_chauffeurs_type.py`), jamais écrits en
  Postgres ; contraindre une FK contre des tables jamais peuplées ferait
  échouer tout `INSERT` (détail dans `orm.py`). Migration
  `55cf8c93e5bf` (`migrations/versions/`). Testé contre un vrai conteneur
  (`tests/integration/test_decisions_repository.py`, comme
  `test_ledger_repository.py` pour le ledger).

## Contenu prévu (V1)

- File de revue humaine (étage 4 de la catégorisation, doc 05 §5) — le
  modèle existe (`decisions.py`), l'écran et la persistance réelle restent
  à faire (doc 17 §9 bloc A/C).
- Circuit de validation avant écriture définitive.
- Signature électronique — prestataire à choisir (ADR-004, devis
  Yousign/Docusign) ; pour la démo, un simulateur d'écran suffit (doc 17 §8).

## Statuts

- **Démo (doc 17 §9, en cours)** : `auto_accept.py` reste actif pour les
  cas nominaux (Karim, Yanis). Bloc A (persistance des décisions) **fini**
  — modèle, implémentation mémoire et Postgres, testées. **Pas encore
  fait** : le branchement à un écran ni à `demo_api.py` (bloc C) — nécessite
  d'abord d'exposer, pour chaque écriture « à trancher », la proposition
  d'origine (`ProposedEntry`) que `construire_ledger()`
  (`demo_chauffeurs_type.py`) calcule puis jette aujourd'hui plutôt que de
  la retourner. Petit refactor à faire avant de coder l'endpoint, pas
  juste un branchement direct.
- **V1 (doc 12, phase 3)** : actif, prestataire de signature tranché,
  persistance Postgres (pas la version mémoire).

## Doc de référence

[doc 05 §5](../../../docs/05-pipeline-categorisation.md#5-étage-4--revue-humaine),
[ADR-004](../../../docs/adr/ADR-004-signature-electronique.md).
