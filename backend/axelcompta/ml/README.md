# ml/

Entraînement, évaluation, registry de modèles. **Hors runtime API** —
personne n'importe `ml` au runtime, les modèles sont chargés comme artefacts
(règle vérifiée par import-linter en CI, doc 03 §3).

**Dépendances :** `core`. Consommé par `categorize/` uniquement via artefact
chargé (`.joblib`), jamais par import direct.

## Ce qui existe déjà et sera réutilisé

Le travail d'entraînement de la baseline a déjà été fait dans l'audit :
[`_AUDIT_DONNEES/entrainer_modele_baseline.py`](../../../_AUDIT_DONNEES/entrainer_modele_baseline.py)
→ [`_AUDIT_DONNEES/modeles/tfidf_logreg_v1.joblib`](../../../_AUDIT_DONNEES/modeles/)
(94,4% accuracy). Ce module sera la version *packagée et réentraînable en
continu* de ce script.

## Statuts

- **Démo (doc 17 §3, §4bis)** : **non prévu.** Le modèle déjà entraîné dans
  l'audit est réutilisé tel quel, aucun réentraînement.
- **V1 (doc 12, phase 2 + doc 07 §5-6)** : boucle de feedback continue,
  MLOps proportionné (pas d'usine à gaz), registry de modèles versionné.

## Doc de référence

[doc 07](../../../docs/07-ml-donnees-entrainement.md) (référence complète : dataset, features, MLOps),
[doc 07 §8](../../../docs/07-ml-donnees-entrainement.md#8-anti-patterns-interdits-à-relire-avant-chaque-décision-ml).
