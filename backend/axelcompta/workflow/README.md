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
  2026-09-07**) : implémentation en mémoire pour les tests et pour brancher
  `demo_api.py` rapidement. **Pas encore fait** : l'implémentation Postgres
  (même pattern que `ledger/repository.py`) — c'est le point de vigilance
  du bloc A (doc 17 §10) : la démo veut une vraie persistance, un
  dictionnaire en mémoire de process ne suffit pas au-delà des tests et
  d'un premier branchement.

## Contenu prévu (V1)

- File de revue humaine (étage 4 de la catégorisation, doc 05 §5) — le
  modèle existe (`decisions.py`), l'écran et la persistance réelle restent
  à faire (doc 17 §9 bloc A/C).
- Circuit de validation avant écriture définitive.
- Signature électronique — prestataire à choisir (ADR-004, devis
  Yousign/Docusign) ; pour la démo, un simulateur d'écran suffit (doc 17 §8).

## Statuts

- **Démo (doc 17 §9, en cours)** : `auto_accept.py` reste actif pour les
  cas nominaux (Karim, Yanis). `decisions.py`/`decisions_memory.py` posent
  le modèle de la vraie décision humaine pour le cas Sophie — **pas encore
  branché** à un écran ni à `demo_api.py` (prochaine étape, bloc C).
- **V1 (doc 12, phase 3)** : actif, prestataire de signature tranché,
  persistance Postgres (pas la version mémoire).

## Doc de référence

[doc 05 §5](../../../docs/05-pipeline-categorisation.md#5-étage-4--revue-humaine),
[ADR-004](../../../docs/adr/ADR-004-signature-electronique.md).
