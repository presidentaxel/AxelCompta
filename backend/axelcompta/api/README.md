# api/

Routes FastAPI, auth, permissions. **Aucune logique métier ici** — n'importe
que les façades publiques de chaque module (`module/service.py`, règle
vérifiée par import-linter en CI, doc 03 §3).

**Dépendances :** façades publiques de tous les modules métier.

## Statuts

- **Démo (doc 17, pivot 2026-09-06)** : toujours un squelette, aucune route.
  L'API qui sert le frontend de démo est volontairement **ailleurs** —
  `axelcompta.demo_api` (composition root comme `demo.py`, doc 18) — pas
  ici, pour ne pas mélanger la vraie API produit (façades des modules
  métier uniquement, cf. contrat import-linter ci-dessous) avec du câblage
  démo qui importe des composition roots. Ce module reste à écrire pour de
  vrai en V1.
- **V1 (doc 12, phase 1.1 + 3)** : auth/MFA, permissions par rôle,
  isolation multi-tenant appliquée au niveau des routes.

## Doc de référence

[doc 03 §7](../../../docs/03-architecture.md#7-auth-rôles-multi-tenant),
[doc 17 §9](../../../docs/17-plan-demo-backend.md#9-semaines-et-jalons) (API de démo : `demo_api.py`, pas ce module),
[doc 19](../../../docs/19-parcours-utilisateur.md).
