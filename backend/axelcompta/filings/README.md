# filings/

Renderers : FEC, PDF de liasse, EDI-TDFC, dossier INPI.

**Dépendances :** `core`, `closing`.

## Fichiers

- `renderer.py` — `FilingRenderer`, façade abstraite.
- `pdf_bouchon.py` — `PdfBouchonRenderer` (doc 17 semaine 0, fait) : liste
  brute des soldes par compte (reportlab), aucune mise en forme réglementaire.

## Statuts

- **Démo (doc 17 semaine 0, fait)** : `PdfBouchonRenderer` produit un PDF
  valide à partir d'une `LiassePivot`. **Semaine 3 (à faire)** :
  sous-ensemble de formulaires réel (bilan simplifié + compte de résultat +
  une case-clé 2065), rendu PDF propre. **Pas de conformité CERFA/DGFiP
  stricte, pas d'EDI, pas d'INPI.**
- **V1 (doc 12, phase 3)** : conformité complète, testée via « Test Compta
  Demat » (spike FEC, doc 12 §0.3), EDI-TDFC (doc 02 — stratégie Partenaire
  EDI en 3 temps), dépôt INPI.

## Doc de référence

[doc 06 §6](../../../docs/06-moteur-comptable.md#6-renderers-filings),
[doc 02](../../../docs/02-cadre-reglementaire.md) (cadre réglementaire FEC/EDI/INPI),
[doc 17 §3, §6](../../../docs/17-plan-demo-backend.md).
