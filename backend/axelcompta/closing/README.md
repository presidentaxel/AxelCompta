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
  (résultat fiscal, aucune réintégration — hors scope démo). Avec
  `ParametresCloture`, délègue à la clôture fiscale ci-dessous.
- `cloture_fiscale.py` (2026-09-23, doc 17 §15) : clôture IS au régime
  simplifié. Écritures d'inventaire (`ecritures_cloture.py` : liquidation
  TVA, IS 695/444), IS (`impot_societes.py` : 15 % jusqu'à 42 500 €
  proratisé, 25 % au-delà), tableaux 2033-A/B (`liasse_2033.py`) et
  2033-C/D/E (`liasse_2033_annexes.py`), le tout dans une `LiassePivot`
  indexée par code officiel (`2033B.310`...). Correspondance comptes →
  rubriques : `rubriques_2033.py`, d'après la notice 2033-NOT-SD, sans
  relecture d'expert-comptable (décision démo). Les écritures d'inventaire
  sont toujours recalculées depuis le grand livre privé d'elles-mêmes
  (`hors_inventaire`) : passées en base à la clôture, elles ne comptent
  pas double et la liasse de l'exercice clos ne bouge pas.
- `affectation.py` + `fiscalite_dividendes.toml` (**2026-09-26**) :
  affectation du résultat. Réserve légale, distribuable, trésorerie
  disponible, scénarios de dividendes chiffrés au PFU de l'année de
  versement, écriture qui solde le résultat. Appelée par
  `axelcompta/affectations.py`.
- `ouverture.py` (**2026-09-26**) : écriture d'à-nouveaux (journal AN) à
  l'ouverture de l'exercice suivant, comptes de bilan repris, résultat en
  120 ou 129. Appelée par `axelcompta/exercices.py`.

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
