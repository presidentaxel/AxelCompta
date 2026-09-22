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
- `orm.py` — mapping SQLAlchemy Core (**étendu le 2026-09-21**) : tables
  `tenants` et `dossiers` (nom, régime TVA recettes, début d'exercice,
  plateformes, mode d'accès bancaire, `contact_nr` Digifactory unique). Un
  seul schéma, aucune colonne RLS.
- `repository.py` / `memory.py` / `postgres.py` (**fait, 2026-09-21**) :
  `DossierRepository`. `lister_par_tenant` est **le** point d'isolation entre
  portefeuilles ; `par_contact_nr` est la table de correspondance
  Digifactory (doc 16 §9 point 5). Enregistrement idempotent, jamais de mise
  à jour silencieuse d'une config comptable.

## Statuts

- **Démo (doc 17 §3)** : les 3 dossiers de démo sont persistés
  (`python -m axelcompta.demo_seed`) et appartiennent à un tenant en base ;
  le gestionnaire ne voit que ceux de son `tenant_id`. **Isolation dans les
  requêtes du repository, pas de RLS Postgres** (V1). Un seul portefeuille
  de démo, pas encore de création de dossier hors amorçage.
- **V1 (doc 12, phase 1.1)** : multi-tenant complet, ~200 dossiers
  indépendants, matrice statut × pack pleinement opérationnelle.

## Doc de référence

[doc 03 §3bis](../../../docs/03-architecture.md#3bis-les-deux-axes-de-configuration--statut-du-dossier--pack-métier),
[doc 06 §7](../../../docs/06-moteur-comptable.md#7-multi-statuts--matrice-de-paramétrage-le-cœur-de-la-versatilité),
[doc 17 §3](../../../docs/17-plan-demo-backend.md#3-coupes-de-scope-assumées).
