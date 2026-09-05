# closing/

Clôture d'exercice, états financiers (bilan, compte de résultat), modèle
pivot de liasse (`LiassePivot`) avant rendu par `filings/`.

**Dépendances :** `core`, `ledger`.

## Fichiers

- `models.py` — `LiassePivot`.
- `service.py` — `ClosingService`, façade abstraite.
- `bilan_simplifie.py` — `ClotureSimplifieeService` (**fait, semaine 3**) :
  balance → compte de résultat (produits/charges via `core.pcg`) → bilan
  (trésorerie, résultat, TVA à payer) → `LiassePivot` avec une case-clé 2065
  (résultat fiscal, aucune réintégration — hors scope démo).

## Statuts

- **Démo (doc 17 semaine 3, fait)** : `ClotureSimplifieeService` produit un
  compte de résultat et un bilan simplifiés qui s'équilibrent réellement
  (trésorerie = résultat + TVA à payer, vérifié en test). Pas de
  rapprochement bancaire, pas de dotations, pas de cadrage TVA de clôture,
  pas de réintégrations fiscales — la checklist complète (doc 06 §5) reste
  V1.
- **V1 (doc 12, phase 3)** : clôture complète, tous les états requis.

## Doc de référence

[doc 06 §5](../../../docs/06-moteur-comptable.md#5-clôture-dexercice-closing).
