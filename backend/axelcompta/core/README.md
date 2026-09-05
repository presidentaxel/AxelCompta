# core/

Types et primitives partagés par tout le reste du monolithe. Le seul module
dont tous les autres ont le droit de dépendre.

**Dépendances :** aucune (module racine).

## Contenu prévu

- `Money` — montants en centimes (int), jamais de `float` pour de l'argent
  (invariant absolu, doc 06 §1).
- `Result` / erreurs typées — pas d'exceptions non gérées sur les chemins
  métier.
- Identifiants typés (dossier, écriture, transaction…) — pas de `str`/`int`
  nu qui se mélange entre entités.
- Dates/temps (fuseaux, exercices comptables).

## Statuts

- **Démo (doc 17, semaine 0)** : `Money` + ids typés, strict minimum pour
  faire tourner le squelette bout-en-bout.
- **V1 (doc 12, phase 1.1)** : `core/` complet avec tests de propriétés
  (property-based testing) sur `Money` et les erreurs.

## Doc de référence

[doc 03 §2](../../../docs/03-architecture.md#2--stack-retenue) (choix Pydantic v2),
[doc 06 §1](../../../docs/06-moteur-comptable.md#1-invariants-absolus-violations--bug-bloquant-jamais-contournable) (invariants Money),
[doc 09 §2](../../../docs/09-strategie-tests.md#2-tests-unitaires-et-de-propriétés-le-socle).
