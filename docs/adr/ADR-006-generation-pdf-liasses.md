# ADR-006 — Génération PDF des liasses fiscales (fidèle CERFA)

**Date :** 2026-06-16
**Statut :** en attente d'évaluation pour la V1 complète (2050/2033/2031) —
POC concret fait sur le 2065 pour la démo (2026-09-05), voir §Résultat du POC.
**Décideurs :** Louis Vedovato

## Contexte

Les liasses fiscales (2050, 2033, 2065, 2031…) doivent être produites en PDF fidèle aux formulaires CERFA officiels. Ces PDF sont destinés à la relecture et signature par le client, puis à l'archivage. Le rendu doit être visuellement conforme pour être accepté par un expert-comptable ou un greffe.

L'architecture retenue (doc 02 §5) sépare la **liasse pivot** (données case-par-case en JSON) des **renderers** (PDF, EDI). Cette ADR concerne uniquement le renderer PDF.

## Contraintes

- Rendu fidèle au formulaire CERFA officiel (police, mise en page, cases cochables).
- Maintenable : les formulaires changent chaque millésime, la mise à jour doit être localisée.
- Self-hosted : les données fiscales ne sortent pas vers un service tiers pour le rendu.
- Python-compatible (backend Python/FastAPI).

## Candidats

| Approche | Outil | Notes |
|----------|-------|-------|
| **Template PDF remplissable** | pypdf / pdfrw | Utiliser les CERFA officiels téléchargeables (DGFiP publie les PDF remplissables) comme templates, remplir les champs AcroForm programmatiquement. Simple, fidèle par construction. Risque : si DGFiP modifie les noms de champs entre millésimes, mapping à maintenir. |
| **Génération HTML → PDF** | WeasyPrint + template Jinja2 | HTML/CSS reproduisant le formulaire, converti en PDF. Flexible, maintenable, mais fidélité visuelle dépend de la qualité du template HTML (travail initial non négligeable). |
| **ReportLab** | ReportLab (lib Python) | Génération programmatique bas niveau. Contrôle total mais verbose et long à implémenter. |

## Décision provisoire

**Template PDF remplissable (pypdf + AcroForm)** est le point de départ le plus pragmatique : les CERFA officiels sont déjà les formulaires, on remplit juste les champs. Moins de risque de divergence visuelle.

Si les CERFA DGFiP n'ont pas assez de champs AcroForm nommés (certains millésimes ont des PDFs scannés sans AcroForm), basculer sur WeasyPrint avec un template HTML.

## Action requise

- [x] Télécharger un CERFA (2065-SD, millésime 2026 — le plus récent
      disponible, pas 2025) : `backend/axelcompta/filings/cerfa/2065-sd_2026.pdf`.
- [x] Vérifier la présence de champs AcroForm : **absents** sur ce
      millésime (`pypdf.PdfReader.get_fields()` renvoie `None`) — le
      scénario de repli anticipé ci-dessus, pas le candidat de départ.
- [x] POC pypdf : 1 case remplie (Cadre C.1, doc 17 §3 « case-clé 2065 »)
      par **overlay reportlab** (pas de l'AcroForm, puisqu'il n'y en a
      pas) — coordonnées repérées via les bordures de cellule réelles du
      PDF (pdfplumber), pas devinées. Voir `filings/cerfa_2065.py`.
- [ ] Télécharger et vérifier 2050, 2033, 2031 (pas fait — hors scope démo,
      2065 seul demandé).
- [ ] POC sur un formulaire à tableaux denses (2050/2033 : bien plus de
      cases que le 2065, qui n'est qu'un récapitulatif) — le 2065 ne
      valide que la mécanique overlay, pas sa tenue à l'échelle.
- [ ] Décision finale sur l'outil pour toute la liasse (2050 à 2059G) —
      **overlay reportlab par coordonnées** fonctionne mais suppose de
      retrouver/maintenir les coordonnées à chaque millésime (pas de
      garde-fou si DGFiP change la mise en page — contrairement à un vrai
      AcroForm nommé, un overlay mal aligné ne lève aucune erreur, il faut
      une vérification visuelle à chaque millésime). À réévaluer en phase 3
      avec le volume réel de cases (2050 en a des dizaines).

## Résultat du POC (2026-09-05, doc 17 « une case-clé 2065 »)

Le 2065-SD n'est qu'un **récapitulatif** (Cadre C : résultat fiscal,
plus-values, abattements...) — la vraie liasse détaillée (bilan, compte de
résultat case par case) est sur des tableaux séparés, 2050 à 2059G en réel
normal ou 2033 A à G en réel simplifié, non couverts par ce POC.

Ce PDF reste **une aide à la relecture humaine, pas une télédéclaration** :
le dépôt légal du 2065 est obligatoirement dématérialisé par EDI/EFI (doc 02,
statut Partenaire EDI), jamais par PDF — aucun outil de rendu ne change ça.
