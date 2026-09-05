# workflow/

Validation, circuit de relecture humaine, signature électronique. C'est le
seul module autorisé à transformer une `ProposedEntry` (sortie de
`categorize/`) en écriture réelle via `ledger/`.

**Dépendances :** `core`, `categorize`, `ingestion` (types transaction),
`ledger`.

## Fichiers

- `auto_accept.py` — `construire_ecriture_categorisee()` (**fait, semaine 2**) :
  stand-in minimal, accepte toute `ProposedEntry` sans validation humaine et
  construit une écriture 512/compte-catégorie (pas de ventilation TVA — ça,
  c'est réservé au settlement plateforme, `ingestion/ecritures_settlement.py`).
  **Pas l'architecture cible** : la vraie file de revue (doc 05 §5) reste à
  construire, ceci ne fait que satisfaire la règle de dépendance (« seul
  workflow transforme une ProposedEntry en écriture ») pour que la démo
  tourne sans revue humaine.

## Contenu prévu (V1)

- File de revue humaine (étage 4 de la catégorisation, doc 05 §5).
- Circuit de validation avant écriture définitive.
- Signature électronique — prestataire à choisir (ADR-004, devis
  Yousign/Docusign).

## Statuts

- **Démo (doc 17 §3, semaine 2)** : `auto_accept.py` seulement — **toujours
  pas de vraie revue humaine ni de signature électronique**, doc 17 §3 les
  exclut explicitement.
- **V1 (doc 12, phase 3)** : actif, prestataire de signature tranché.

## Doc de référence

[doc 05 §5](../../../docs/05-pipeline-categorisation.md#5-étage-4--revue-humaine),
[ADR-004](../../../docs/adr/ADR-004-signature-electronique.md).
