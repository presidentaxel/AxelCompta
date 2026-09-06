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
  (**fait, 2026-09-05, complété le même jour suite à « il me faut tout sur
  le dossier »**) : overlay sur le **vrai formulaire officiel** 2065-SD
  (téléchargé depuis impots.gouv.fr). Cases remplies : résultat fiscal
  (Cadre C.1), exercice ouvert/clos, régime réel normal, comptabilité
  informatisée (OUI + logiciel "AxelCompta") — tous des faits qu'on connaît
  vraiment. **Cadre A (désignation, SIRET, adresse) reste blanc exprès** :
  aucune identité d'entreprise n'est modélisée, et un vrai dossier
  historique est pseudonymisé à l'audit (doc 07 §2.2) — inventer un nom ou
  un SIRET serait fabriquer une donnée, pas en afficher une vraie. Voir
  ADR-006 pour le POC complet et ses limites — **toujours pas une
  télédéclaration réelle** (EDI/EFI obligatoire, statut Partenaire EDI,
  doc 02).
- `fec.py` — `exporter_fec()` (**fait, 2026-09-05**) : le FEC, 18 colonnes
  normées (art. A.47 A-1), même schéma que `_AUDIT_DONNEES/extraire_fec.py`.
  **Le format légal exigé en cas de contrôle fiscal** — demandé explicitement
  suite à « s'il est faux, on ne sait pas » (une liasse sans le détail
  derrière ne permet pas de tracer une erreur). Pas passé dans « Test Compta
  Demat » ni comparé octet à octet à un FEC de référence (doc 09 §3) — la
  checklist complète reste V1.
- `export_comptable.py` — `exporter_grand_livre()`/`exporter_balance()`
  (**fait, 2026-09-05**) : CSV, doc 06 §6 (« pour l'expert-comptable du
  client »). Réutilisent les mêmes libellés de compte que le FEC.

## Statuts

- **Démo (doc 17 semaine 3, fait)** : `PdfLiasseSimplifieeRenderer` produit
  un PDF qui présente un compte de résultat et un bilan simplifiés (plus le
  dump brut de comptes de la semaine 0/2, remplacé). `PdfCerfa2065Renderer`
  ajoute la fidélité visuelle au vrai formulaire pour la case résultat.
  `fec.py`/`export_comptable.py` ajoutent le détail (journal, grand livre,
  balance) qui manquait derrière les chiffres de la liasse.
- **V1 (doc 12, phase 3)** : conformité complète sur toute la liasse
  (2050-2059G/2033A-G, pas seulement le récapitulatif 2065), testée via
  « Test Compta Demat » (spike FEC, doc 12 §0.3), EDI-TDFC (doc 02 —
  stratégie Partenaire EDI en 3 temps, la seule vraie voie de dépôt légal),
  dépôt INPI.

## Doc de référence

[doc 06 §6](../../../docs/06-moteur-comptable.md#6-renderers-filings),
[doc 02](../../../docs/02-cadre-reglementaire.md) (cadre réglementaire FEC/EDI/INPI),
[doc 17 §3, §6](../../../docs/17-plan-demo-backend.md).
