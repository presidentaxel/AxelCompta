# ADR-007 — Modèle ML V1 pour la catégorisation des transactions

**Date :** 2026-06-25  
**Statut :** DÉCIDÉ, **amendé le 2026-09-21** (voir l'encadré ci-dessous)  
**Décideurs :** Louis Vedovato

> **Amendement du 2026-09-21 : le chiffre de 94,4 % ne tient pas.**
> Les catégories du dataset sont dérivées du compte PCG (mapping
> `packs_vtc/mapping_pcg_categorie.csv`). Ajouter `[PCG{3chars}]` au libellé
> revient donc à donner la réponse au modèle. Or sur une transaction bancaire
> brute, le compte PCG n'existe pas encore : c'est ce que le pipeline doit
> produire. **Le token PCG est exclu des features en production.**
>
> Mesure refaite le 2026-09-21 avec le split par dossier de
> `entrainer_modele_baseline.py` (58 dossiers train, 14 test) :
>
> | Features | Exactitude |
> |---|---|
> | libellé seul | 76,9 % |
> | libellé + bucket de montant (**modèle retenu**) | **79,5 %** |
> | libellé + montant + token PCG (inutilisable à l'inférence) | 96,3 % |
>
> Le 77,0 % « libellé seul » du tableau ci-dessous se retrouve, le 94,4 % est
> le score du token PCG. **Chiffre de référence : 79,5 %**, mesuré contre les
> labels du mapping et non contre une relecture humaine. La vraie précision
> attend les 500 lignes relues (`_AUDIT_DONNEES/resultats/`, doc 12 §0.2).
>
> Deux réserves de traçabilité. Le spike d'origine (code, splits, scripts
> sentence-transformers et CamemBERT, « 500 lignes annotées à la main ») n'est
> plus dans le repo : le tableau de benchmark et le classement des modèles sont
> donc **non vérifiables**, à lire comme indicatifs. Et le fichier
> `tfidf_logreg_v1.joblib` actuel a été réécrit le 2026-09-02 par
> `entrainer_modele_baseline.py` : 23 classes, n-grammes de caractères 2-4,
> bucket de montant, pas de token PCG. La section « Décision » plus bas décrit
> le modèle d'origine (n-grammes 2-5 avec token PCG), pas celui-là.

## Contexte

Le pipeline de catégorisation (doc 05) requiert un modèle ML capable de mapper
(libellé bancaire brut, compte PCG) → catégorie de la taxonomie VTC (18 classes).
Le spike Phase 0 a benchmarké 4 approches sur 48 042 transactions labellisées
(pack VTC, 2017-2025), évalué sur 500 lignes annotées à la main.

## Benchmark Phase 0

| Modèle | Accuracy | Inférence CPU | Coût déploiement |
|--------|----------|--------------|-----------------|
| TF-IDF (libellé seul) | 77.0 % | < 0.1 ms | Minimal |
| **TF-IDF + token PCG préfixe** | **94.4 %** | **< 0.1 ms** | **Minimal** |
| sentence-transformers MiniLM-L12 | 82.8 % | 0.2 ms | Moyen |
| sentence-transformers mpnet-base | 81.6 % | 0.4 ms | Moyen |
| CamemBERT fine-tuné (10 époques) | 92.0 % | ~50 ms | Élevé (GPU recommandé) |

## Décision

**TF-IDF char n-gram (2,5) + LogisticRegression + token `[PCG{3chars}]` en suffixe
du libellé normalisé.**

Fichier modèle : `_AUDIT_DONNEES/modeles/tfidf_logreg_v1.joblib`

## Justification

1. **Le token PCG est la clé.** Passer de 77 % à 94.4 % avec un seul token prouve
   que l'ambiguïté vient de la confusion commission/recette sur le même marchand
   (UBER sur 622xxx vs 706xxx). Ce signal est mieux exploité par TF-IDF que par des
   embeddings pré-entraînés qui n'ont jamais vu `[PCG622]`.

2. **Les libellés VTC sont courts et bruités.** Les character n-grams (2,5) encaissent
   les troncatures (`VINCI AUT`, `CARREF MKT`) mieux que des embeddings entraînés sur
   des phrases complètes. Les embeddings figés (-12 pts) et CamemBERT fine-tuné (-2 pts)
   le confirment.

3. **Simplicité opérationnelle.** < 0.1 ms/inférence, pas de GPU, 1 fichier .joblib
   de quelques Mo, rechargeable en mémoire en < 1 s. Idéal pour un monolithe modulaire
   à 1-2 devs (doc 03 §1).

4. **Calibration isotonique** à appliquer avant la mise en production : les probabilités
   brutes de LogReg ne sont pas bien calibrées. `sklearn.calibration.CalibratedClassifierCV`
   sur le set de validation (doc 05 §ML contract).

## Conséquences

- Le module `axelcompta/categorize/` chargera `tfidf_logreg_v1.joblib` + calibration.
- Le preprocessing normalise le libellé et ajoute `[PCG{3chars}]` avant encode.
- Si le dataset passe > 200 k exemples ou si la précision plafonne sur de nouvelles
  catégories, réévaluer LightGBM + embeddings figés (doc 07 §3.2 step 3).
- CamemBERT reste archivé comme benchmark ; ne pas le déployer en V1.

## Décision sur l'étape suivante (doc 07 §3.2)

Le challenger LightGBM + features mixtes (§3.1 : montant log-bucketé, jour de semaine,
récurrence) n'est pas nécessaire pour le V1. À planifier si besoin en Phase 2.
