# Audit du dataset — 10 ans d'historique

> Référence : [doc 07 §2.1](../docs/07-ml-donnees-entrainement.md#21-audit-avant-tout-entraînement-livrable--rapport-de-qualité-dataset),
> §3.4 (classes rares), §4 (évaluation), [ADR-007](../docs/adr/ADR-007-modele-ml-categorisation.md).
>
> **Ce que le score du spike Phase 0 (94.4 % TF-IDF+PCG, 48 042 transactions,
> 500 lignes annotées) répond déjà — et ce qu'il ne répond pas** : c'est une
> précision globale top-1. Il ne dit rien sur les droits RGPD, la qualité des
> labels, la dérive temporelle, la précision par classe à enjeu, ni sur le
> risque de fuite du split. Ce dossier couvre les deux : ce qui est déjà acquis
> et ce qu'il reste à produire pour boucler le livrable « rapport de qualité
> dataset » exigé avant tout entraînement en production.

## Ce qui est déjà acquis (via le spike ADR-007)

- [x] Le lien **libellé bancaire ↔ compte PCG** existe sur l'échantillon
      benchmarké (48 042 transactions, le token `[PCG{3chars}]` a été extrait
      → le risque n°1 n'est pas confirmé partout, seulement sur cet échantillon).
- [x] Précision globale mesurée (94.4 %) sur 500 lignes annotées à la main.

## Ce qu'il reste à produire (le vrai livrable d'audit)

| # | Item | Automatisable | Script |
|---|------|----------------|--------|
| 1 | Inventaire : formats, périodes couvertes, nb dossiers/lignes, droit d'usage RGPD | Partiel (le RGPD est manuel — vérifier le fondement juridique du réemploi de ces 10 ans de données clients pour entraîner un modèle) | `audit_dataset.py --step inventaire` |
| 2 | **Lien libellé bancaire ↔ compte PCG existe-t-il sur la totalité des 10 ans**, pas juste sur les 48k du spike (certains formats d'export FEC ne portent pas le libellé bancaire d'origine) | Oui | `audit_dataset.py --step lien-pcg` |
| 3 | Qualité des labels : qui a imputé (comptable rigoureux vs stagiaire), échantillonner 500 lignes et faire relire par un tiers | Non — manuel, mais le script tire l'échantillon aléatoire à relire | `audit_dataset.py --step echantillon-labels` |
| 4 | Dérive temporelle : enseignes disparues, pratiques d'imputation qui ont changé | Oui (stats descriptives par année) | `audit_dataset.py --step derive-temporelle` |
| 5 | Distribution des classes + **liste des classes rares** (< N_min, indicativement 100) et leur politique (doc 07 §3.4) | Oui | `audit_dataset.py --step distribution-classes` |
| 6 | Vérifier l'**absence de fuite** : split train/validation/test bien fait par dossier ET par période (pas ligne à ligne aléatoire) — sinon le 94.4 % est optimiste | Oui, si vous avez conservé les fichiers de split du spike | `audit_dataset.py --step verif-fuite` |
| 7 | **Précision par classe**, surtout classes à enjeu (immobilisations, rémunérations, TVA intracom) ≥ 95 % ou classe exclue de l'auto-validation | Oui, si vous avez le modèle `.joblib` + le jeu de test | `audit_dataset.py --step precision-classe` |
| 8 | Matrice de confusion inspectée à la main — lister les erreurs graves (charge ↔ immobilisation) | Le script génère la matrice, la lecture reste manuelle | `audit_dataset.py --step precision-classe` (sort la matrice en CSV) |

## Schéma attendu des fichiers d'entrée

Le script attend un CSV `transactions.csv` avec au minimum ces colonnes
(adapter les noms via `--col-*` si votre export diffère) :

| Colonne | Exemple | Note |
|---|---|---|
| `dossier_id` | `CHF-00123` | identifiant du dossier/chauffeur |
| `date` | `2021-03-14` | date de la transaction |
| `libelle_brut` | `RELAIS TOTAL A6` | libellé bancaire d'origine — **son absence = risque n°1 confirmé sur cette ligne** |
| `montant` | `-60.00` | signé |
| `compte_pcg` | `60611` | compte PCG imputé historiquement |
| `categorie` | `carburant` | classe de la taxonomie VTC — vérité terrain |
| `source_format` | `FEC` / `export_logiciel` / `excel` | pour l'inventaire §1 et la dérive §4 |

Pour les étapes 6-7 (fuite, précision par classe), fournir en plus :
- `--train-set train.csv` / `--test-set test.csv` (mêmes colonnes + `dossier_id`)
- `--model modeles/tfidf_logreg_v1.joblib` (le modèle issu d'ADR-007)

## Utilisation

```bash
cd _AUDIT_DONNEES
python audit_dataset.py --transactions transactions.csv --step all
# ou une étape à la fois, ex :
python audit_dataset.py --transactions transactions.csv --step distribution-classes --n-min 100
```

Chaque étape écrit ses résultats dans `sortie/` (CSV + un bloc à coller dans
`rapport_audit_dataset.md`). Les étapes 1 et 3 laissent des `[À COMPLÉTER]`
pour la partie humaine (droit RGPD, relecture des 500 lignes).

## Confidentialité

Ce dossier contiendra des données clients réelles (libellés bancaires,
montants, éventuellement noms si pas encore pseudonymisés). **Rien dans
`_AUDIT_DONNEES/` ne doit être commité** à part ce README, `audit_dataset.py`
et `rapport_audit_dataset_TEMPLATE.md` — voir `.gitignore` mis à jour à la
racine.
