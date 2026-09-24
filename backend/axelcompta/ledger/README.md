# ledger/ ❤️

Le moteur comptable **pur** : écritures, journaux, balance, immobilisations,
TVA. Le cœur du produit — c'est le module qui doit être juste avant tout le
reste.

**Dépendances : `core` uniquement.** Jamais `categorize`, jamais `ml`, jamais
`api` (règle vérifiée par import-linter en CI, doc 03 §3).

## Invariants absolus (doc 06 §1 — violation = bug bloquant, jamais contournable)

- Montants toujours en centimes (`int`), jamais de `float`.
- Toute écriture équilibrée (débit = crédit) ou rejetée, jamais persistée
  déséquilibrée.
- Immutabilité : une écriture validée ne se modifie pas, elle se contre-passe.

## Fichiers

- `models.py` — domaine pur (`Ecriture`, `LigneEcriture`, `Journal`, `Sens`).
- `invariants.py` — `verifier_equilibre` : pur, sans I/O, la seule autorité sur
  l'équilibre débit/crédit.
- `service.py` — `LedgerService`, la façade abstraite (seule chose que `api`
  a le droit d'importer, doc 03 §3).
- `memory.py` — `InMemoryLedgerService` : implémentation en mémoire pour la
  démo (doc 17 semaine 0), sans Postgres.
- `orm.py` / `repository.py` — `PostgresLedgerService` : implémentation
  réelle contre Postgres (SQLAlchemy Core). `orm.py` définit les tables,
  séparé de `models.py` pour garder le domaine pur (doc 08 §2.1).

## Statuts

- **Démo (doc 17 semaine 0, fait)** : `verifier_equilibre` + les deux
  implémentations de `LedgerService` (mémoire et Postgres) tournent contre le
  golden test doc 17 §7, **sans ventilation TVA** (512/706 bruts). La
  ventilation réelle (512/622x/44566/706/44571) arrive semaine 2 (doc 13 §5.3).
- **V1 (doc 12, phase 1.2-1.3)** : moteur complet, immobilisations,
  rapprochement bancaire (doc 06 §4), tous les templates du pack VTC (doc 06 §3).

## Doc de référence

[doc 06](../../../docs/06-moteur-comptable.md) (référence complète du module),
[doc 13 §5](../../../docs/13-integrations-plateformes.md#5-génération-décritures-depuis-un-settlement-réconcilié) (templates de settlement),
[doc 17 §7](../../../docs/17-plan-demo-backend.md#7-golden-test-de-sortie).
