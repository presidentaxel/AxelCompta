# ADR-006 — Génération PDF des liasses fiscales (fidèle CERFA)

**Date :** 2026-06-16
**Statut :** en attente d'évaluation — décision à prendre en phase 3
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

- [ ] Télécharger les CERFA 2050, 2033, 2065, 2031 millésime 2025
- [ ] Vérifier la présence et les noms des champs AcroForm dans chaque formulaire
- [ ] POC pypdf : remplir 5 cases d'un 2050 depuis la liasse pivot
- [ ] Mettre à jour cet ADR avec la décision finale
