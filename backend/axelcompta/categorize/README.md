# categorize/

Pipeline de catégorisation hybride en étages : règles dures → modèle ML →
LLM arbitre → revue humaine. Produit des `ProposedEntry` — seul `workflow`
peut les transformer en écritures réelles via `ledger`, après validation
(règle de dépendance CI, doc 03 §3).

**Dépendances :** `core`, `packs`, `ingestion` (types `NormalizedTransaction` en
entrée, doc 13 §2.2), `documents` (matching pièce, V1 seulement).
**N'a pas le droit d'écrire dans `ledger` directement.**

## Les 4 étages (V1, doc 05 §1)

1. **Règles dures** — déterministe, biais maîtrisé (regex du pack).
2. **Modèle ML** — TF-IDF + régression logistique / gradient boosting sur ce
   que les règles ne couvrent pas.
3. **LLM arbitre** — cas ambigus restants, via pseudonymisation en amont
   (doc 10 §4).
4. **Revue humaine** — filet final, explicabilité de bout en bout (doc 05 §7).

## Ce qui existe déjà et sera réutilisé

- [`_AUDIT_DONNEES/modeles/tfidf_logreg_v1.joblib`](../../../_AUDIT_DONNEES/modeles/) —
  94,4% accuracy, **aucun réentraînement nécessaire** pour la démo.
- [`_AUDIT_DONNEES/resultats/fec_ml_taxonomie.csv`](../../../_AUDIT_DONNEES/resultats/) —
  36 152 lignes labellisées, déjà rejoué par `FileImportProvider` (chemin C,
  `ingestion/providers/file_import.py`, fait en semaine 1).

## Fichiers

- `models.py` — `ProposedEntry`, `Etage`.
- `pipeline.py` — `CategorizationPipeline`, façade abstraite.
- `ml_fallback.py` — charge `tfidf_logreg_v1.joblib` comme artefact (jamais
  `import axelcompta.ml`, doc 03 §3), reproduit exactement le featurizing de
  `entrainer_modele_baseline.py` (bucket de montant + libellé). Dégradation
  explicite si le fichier est absent (`ModeleMlIndisponible`, gitignoré).
- `rules_and_ml.py` — `RulesAndMlPipeline` (**fait, semaine 2**) : étage 1
  (première règle du pack qui matche) puis étage 2 (ML si aucune règle ne
  matche, ou catégorie par défaut à confiance nulle si le modèle est absent).

## Statuts

- **Démo (doc 17 §3, semaine 2, fait)** : étages 1 et 2 seulement (règles +
  ML existant, aucun réentraînement). **Pas de LLM d'arbitrage** — pas de
  stage 3 du tout, pas même un stub. Pas de revue humaine / UI de validation
  (la transformation en écriture passe par `workflow/auto_accept.py`, qui
  accepte tout sans revue — doc 17 §3).
- **V1 (doc 12, phase 2)** : pipeline complet à 4 étages, boucle de feedback
  continue (doc 07 §5).

## Doc de référence

[doc 05](../../../docs/05-pipeline-categorisation.md) (pipeline complet),
[doc 07](../../../docs/07-ml-donnees-entrainement.md) (ML, données, MLOps),
[doc 17 §3, §4bis](../../../docs/17-plan-demo-backend.md).
