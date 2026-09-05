# workflow/

Validation, circuit de relecture humaine, signature électronique. C'est le
seul module autorisé à transformer une `ProposedEntry` (sortie de
`categorize/`) en écriture réelle via `ledger/`.

**Dépendances :** `core`, `categorize`, `ledger`.

## Contenu prévu (V1)

- File de revue humaine (étage 4 de la catégorisation, doc 05 §5).
- Circuit de validation avant écriture définitive.
- Signature électronique — prestataire à choisir (ADR-004, devis
  Yousign/Docusign).

## Statuts

- **Démo (doc 17 §3)** : **non prévu.** Ni revue humaine, ni signature
  électronique dans le scope démo.
- **V1 (doc 12, phase 3)** : actif, prestataire de signature tranché.

## Doc de référence

[doc 05 §5](../../../docs/05-pipeline-categorisation.md#5-étage-4--revue-humaine),
[ADR-004](../../../docs/adr/ADR-004-signature-electronique.md).
