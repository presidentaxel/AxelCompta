# api/

Routes FastAPI, auth, permissions. **Aucune logique métier ici** — n'importe
que les façades publiques de chaque module (`module/service.py`, règle
vérifiée par import-linter en CI, doc 03 §3).

**Dépendances :** façades publiques de tous les modules métier.

## Statuts

- **Démo (doc 17)** : minimal, pas prioritaire avant semaine 4. Pas d'auth,
  pas de MFA (accès direct ou trivial, doc 17 §3).
- **V1 (doc 12, phase 1.1 + 3)** : auth/MFA, permissions par rôle,
  isolation multi-tenant appliquée au niveau des routes.

## Doc de référence

[doc 03 §7](../../../docs/03-architecture.md#7-auth-rôles-multi-tenant),
[doc 17 §6](../../../docs/17-plan-demo-backend.md#6-semaine-par-semaine) (front minimal semaine 4, dépend de l'API).
