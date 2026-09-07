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

- **Démo (doc 17 §9)** : `auto_accept.py` reste actif pour les cas
  nominaux (Karim, Yanis). **Bloc A et C finis (2026-09-07)** : la file de
  revue est réelle de bout en bout — `demo_api.py` expose
  `POST .../decision`, le clic dans l'UI déclenche vraiment
  `revue.py`/`decisions_postgres.py`, testé en HTTP réel (`curl`) et dans
  un vrai navigateur (clic → Postgres → rafraîchissement). `auto_accept.py`
  n'est donc plus la seule voie : Sophie passe maintenant par la vraie
  décision humaine, Karim/Yanis restent sur le stand-in (rien à trancher
  chez eux dans la démo).
- `revue.py` — `resoudre_ecriture_a_trancher()`, `CategorieInconnueError`
  (**fait, 2026-09-07**) : reclasse une écriture « à trancher » vers le
  compte réel de la catégorie choisie par l'humain — 455 (SASU/EURL) pour
  « usage_personnel » (doc 06 §3.6), n'importe quel autre compte du pack
  sinon. Montants et sens inchangés : une reclassification, pas un nouveau
  calcul.
- **V1 (doc 12, phase 3)** : actif, prestataire de signature tranché,
  persistance Postgres (pas la version mémoire).

## Doc de référence

[doc 05 §5](../../../docs/05-pipeline-categorisation.md#5-étage-4--revue-humaine),
[ADR-004](../../../docs/adr/ADR-004-signature-electronique.md).
