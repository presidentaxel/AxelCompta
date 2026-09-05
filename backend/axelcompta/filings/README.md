# filings/

Renderers : FEC, PDF de liasse, EDI-TDFC, dossier INPI.

**Dépendances :** `core`, `closing`.

## Fichiers

- `renderer.py` — `FilingRenderer`, façade abstraite.
- `liasse_simplifiee.py` — `PdfLiasseSimplifieeRenderer` (**fait, semaine 3**) :
  compte de résultat + bilan + case-clé 2065, présentation lisible (reportlab).
  **Pas de conformité CERFA/DGFiP, pas d'EDI, pas d'INPI** — c'est écrit
  noir sur blanc dans le PDF lui-même pour qu'on ne s'y trompe jamais.
- `cerfa/2065-sd_2026.pdf` + `cerfa_2065.py` — `PdfCerfa2065Renderer`
  (**fait, 2026-09-05**) : overlay sur le **vrai formulaire officiel**
  2065-SD (téléchargé depuis impots.gouv.fr), une seule case remplie
  (Cadre C.1, résultat fiscal), le reste blanc car hors profil démo (pas
  de groupe, pas de plus-value...). Voir ADR-006 pour le POC complet et ses
  limites — **toujours pas une télédéclaration réelle** (EDI/EFI
  obligatoire, statut Partenaire EDI, doc 02).

## Statuts

- **Démo (doc 17 semaine 3, fait)** : `PdfLiasseSimplifieeRenderer` produit
  un PDF qui présente un compte de résultat et un bilan simplifiés (plus le
  dump brut de comptes de la semaine 0/2, remplacé). `PdfCerfa2065Renderer`
  ajoute la fidélité visuelle au vrai formulaire pour la case résultat.
- **V1 (doc 12, phase 3)** : conformité complète sur toute la liasse
  (2050-2059G/2033A-G, pas seulement le récapitulatif 2065), testée via
  « Test Compta Demat » (spike FEC, doc 12 §0.3), EDI-TDFC (doc 02 —
  stratégie Partenaire EDI en 3 temps, la seule vraie voie de dépôt légal),
  dépôt INPI.

## Doc de référence

[doc 06 §6](../../../docs/06-moteur-comptable.md#6-renderers-filings),
[doc 02](../../../docs/02-cadre-reglementaire.md) (cadre réglementaire FEC/EDI/INPI),
[doc 17 §3, §6](../../../docs/17-plan-demo-backend.md).
