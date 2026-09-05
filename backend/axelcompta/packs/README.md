# packs/

Le deuxième axe de configuration (voir aussi [`tenants/`](../tenants/README.md)
pour le premier) : le **pack métier** — taxonomie de catégories, règles
système, templates d'écritures sectoriels, paramètres d'anomalies, adaptation
ML. Un pack est un ensemble de **données versionnées** (+ ses tests), pas du
code : `if secteur == "vtc"` est interdit hors de ce module.

**Dépendances :** `core`.

## Ce qui existe déjà et sera réutilisé

Le pack **VTC** (le premier) est déjà largement dégrossi dans l'audit,
inchangé à cet endroit :

- [`_AUDIT_DONNEES/packs_vtc/taxonomie.md`](../../../_AUDIT_DONNEES/packs_vtc/taxonomie.md) — ~40-80 classes.
- [`_AUDIT_DONNEES/packs_vtc/regles_regex.csv`](../../../_AUDIT_DONNEES/packs_vtc/regles_regex.csv) — 24 règles regex.
- [`_AUDIT_DONNEES/packs_vtc/mapping_pcg_categorie.csv`](../../../_AUDIT_DONNEES/packs_vtc/mapping_pcg_categorie.csv) — 61 mappings PCG, 18 catégories.

`packs/` sera la version *packagée et testée* de ces artefacts pour tourner
en runtime API ; en attendant, ce module charge les fichiers de l'audit
directement.

## Statuts

- **Démo (doc 17 §4bis)** : pack VTC réduit aux ~15 catégories les plus
  fréquentes, base du catégoriseur à règles.
- **V1 (doc 12, phase 1.1 + 0.2)** : taxonomie complète construite avec le
  comptable du client, table de mapping comptes historiques → taxonomie.

## Doc de référence

[doc 03 §3bis](../../../docs/03-architecture.md#3bis-les-deux-axes-de-configuration--statut-du-dossier--pack-métier),
[doc 07 §3](../../../docs/07-ml-donnees-entrainement.md#3-features-et-modèle).
