# filings/

Renderers : FEC, PDF de liasse, EDI-TDFC, dossier INPI.

**Dépendances :** `core`, `closing`.

## Fichiers

- `renderer.py` — `FilingRenderer`, façade abstraite.
- `liasse_simplifiee.py` — `PdfLiasseSimplifieeRenderer` (**fait, semaine 3**) :
  compte de résultat + bilan + case-clé 2065, présentation lisible (reportlab).
  **Pas de conformité CERFA/DGFiP, pas d'EDI, pas d'INPI** — c'est écrit
  noir sur blanc dans le PDF lui-même pour qu'on ne s'y trompe jamais.

## Statuts

- **Démo (doc 17 semaine 3, fait)** : `PdfLiasseSimplifieeRenderer` produit
  un PDF qui présente un compte de résultat et un bilan simplifiés (plus le
  dump brut de comptes de la semaine 0/2, remplacé).
- **V1 (doc 12, phase 3)** : conformité complète, testée via « Test Compta
  Demat » (spike FEC, doc 12 §0.3), EDI-TDFC (doc 02 — stratégie Partenaire
  EDI en 3 temps), dépôt INPI.

## Doc de référence

[doc 06 §6](../../../docs/06-moteur-comptable.md#6-renderers-filings),
[doc 02](../../../docs/02-cadre-reglementaire.md) (cadre réglementaire FEC/EDI/INPI),
[doc 17 §3, §6](../../../docs/17-plan-demo-backend.md).
