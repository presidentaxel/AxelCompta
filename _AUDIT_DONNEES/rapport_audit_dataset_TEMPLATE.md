# Rapport d'audit du dataset — 10 ans d'historique

> Livrable exigé par doc 07 §2.1, avant tout entraînement en production.
> Dupliquer ce fichier en `rapport_audit_dataset.md` (gitignoré) et compléter.

**Date de l'audit :** [À COMPLÉTER]
**Auteur :** [À COMPLÉTER]
**Version du dataset auditée :** [À COMPLÉTER — hash / date d'export]

## 1. Inventaire

- Formats source : [coller sortie/1_inventaire.csv]
- Période couverte : [À COMPLÉTER]
- Nombre de dossiers / lignes : [À COMPLÉTER]
- **Droit d'usage RGPD** : base légale du réemploi de ces 10 ans de données
  clients pour entraîner un modèle (consentement contractuel ? intérêt
  légitime documenté ?) — [À COMPLÉTER, voir doc 02 §8]

## 2. Lien libellé bancaire ↔ compte PCG (risque n°1)

- Taux de lien rompu global : [coller sortie/2_lien_pcg_par_ligne.csv]
- Par format source : [coller sortie/2_lien_pcg_par_format.csv]
- **Conclusion** : le lien est-il fiable sur la totalité des 10 ans, ou
  seulement sur une partie (ex. exports logiciel récents mais pas les FEC
  anciens) ? [À COMPLÉTER]

## 3. Qualité des labels

- Échantillon relu : sortie/3_echantillon_labels_a_relire.csv (n=[À COMPLÉTER])
- Relu par : [À COMPLÉTER]
- Taux d'accord avec la catégorie historique : [À COMPLÉTER]
- Origine des imputations (comptable senior / stagiaire / import brut) : [À COMPLÉTER]

## 4. Dérive temporelle

- [coller sortie/4_derive_par_annee.csv et 4_derive_enseignes.csv]
- Faut-il pondérer les années récentes à l'entraînement ? [À COMPLÉTER]

## 5. Distribution des classes et classes rares

- [coller sortie/5_distribution_classes.csv]
- Classes rares (< N_min=[À COMPLÉTER] exemples) et politique assignée (doc 07 §3.4) :

| Classe | N exemples | Enjeu | Politique |
|---|---|---|---|
| [À COMPLÉTER] | | | |

## 6. Vérification anti-fuite du split (spike ADR-007)

- Dossiers communs train/test : [coller sortie/6_dossiers_communs.csv]
- **Conclusion** : le split du spike était-il propre (par dossier ET période)
  ou le 94.4 % est-il optimiste ? [À COMPLÉTER]

## 7-8. Précision par classe et matrice de confusion

- [coller sortie/7_precision_par_classe.csv]
- Classes sous 95 % (à exclure de l'auto-validation si enjeu élevé — immos,
  rémunérations, TVA intracom) : [À COMPLÉTER]
- Erreurs graves identifiées dans sortie/7_matrice_confusion.csv (ex. charge
  ↔ immobilisation) : [À COMPLÉTER]

## Conclusion : le dataset est-il exploitable en l'état ?

[À COMPLÉTER — go/no-go, actions correctives avant entraînement de production]
