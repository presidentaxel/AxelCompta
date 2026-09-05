# tenants/

Tenants (mode portefeuille ou mono), dossiers, et l'un des deux axes de
configuration : le **statut** (forme juridique, régime fiscal, régime TVA).
L'autre axe (le **pack métier**) vit dans [`packs/`](../packs/README.md).

Chaque dossier est indépendant et porte sa configuration complète en propre —
le tenant ne fournit que des valeurs de pré-remplissage à la création, jamais
d'héritage implicite (doc 03 §3bis, doc 06 §7).

**Dépendances :** `core`.

## Contenu prévu (V1)

- Modèles tenant + dossier, RLS (Row-Level Security Postgres) + middleware
  d'isolation, suite de tests d'isolation dédiée.
- Matrice de configuration statut × régime (doc 06 §7), en données
  versionnées, colonnes complètes IS et option IR opérationnelles.
- Option IR bornée : date de début, décompte des 5 exercices, alertes N-1/N,
  bascule IS tracée, changement de régime par avenant daté.

## Fichiers

- `models.py` — domaine pur (`Tenant`, `Dossier`).
- `orm.py` — mapping SQLAlchemy Core de `Dossier` (doc 17 semaine 0, fait) :
  table `dossiers`, un seul schéma, aucune colonne RLS.

## Statuts

- **Démo (doc 17 §3, semaine 0 fait pour la persistance)** : réduit à
  l'extrême — **un seul profil dossier codé en dur** (SASU, IS, TVA réel
  normal, assujetti 10%, pas d'option IR, pas de franchise), 2-3 dossiers de
  test max. **Pas de multi-tenant, pas de RLS.**
- **V1 (doc 12, phase 1.1)** : multi-tenant complet, ~200 dossiers
  indépendants, matrice statut × pack pleinement opérationnelle.

## Doc de référence

[doc 03 §3bis](../../../docs/03-architecture.md#3bis-les-deux-axes-de-configuration--statut-du-dossier--pack-métier),
[doc 06 §7](../../../docs/06-moteur-comptable.md#7-multi-statuts--matrice-de-paramétrage-le-cœur-de-la-versatilité),
[doc 17 §3](../../../docs/17-plan-demo-backend.md#3-coupes-de-scope-assumées).
