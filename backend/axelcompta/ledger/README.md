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

## Statuts

- **Démo (doc 17 §7, golden test)** : doit reproduire noir sur blanc
  l'exemple Uber chiffré en doc 13 §5.3 — settlement 1 040,00 € TTC,
  commission 192,00 € TTC, écriture ventilée (512/622x/44566/706/44571)
  équilibrée. C'est le critère « le concept est validé ».
- **V1 (doc 12, phase 1.2-1.3)** : moteur complet, immobilisations,
  rapprochement bancaire (doc 06 §4), tous les templates du pack VTC (doc 06 §3).

## Doc de référence

[doc 06](../../../docs/06-moteur-comptable.md) (référence complète du module),
[doc 13 §5](../../../docs/13-integrations-plateformes.md#5-génération-décritures-depuis-un-settlement-réconcilié) (templates de settlement),
[doc 17 §7](../../../docs/17-plan-demo-backend.md#7-golden-test-de-sortie).
