# closing/

Clôture d'exercice, états financiers (bilan, compte de résultat), modèle
pivot de liasse (`LiassePivot`) avant rendu par `filings/`.

**Dépendances :** `core`, `ledger`.

## Fichiers

- `models.py` — `LiassePivot`.
- `service.py` — `ClosingService`, façade abstraite.
- `bouchon.py` — `BouchonClosingService` (doc 17 semaine 0, fait) : solde brut
  par compte à partir du grand livre, aucune distinction bilan/compte de
  résultat.

## Statuts

- **Démo (doc 17 semaine 0, fait)** : `BouchonClosingService` tourne contre
  `InMemoryLedgerService`. **Semaine 3 (à faire)** : vraie balance → compte de
  résultat / bilan simplifié, `LiassePivot` réduit au strict nécessaire pour
  le récit de démo.
- **V1 (doc 12, phase 3)** : clôture complète, tous les états requis.

## Doc de référence

[doc 06 §5](../../../docs/06-moteur-comptable.md#5-clôture-dexercice-closing).
