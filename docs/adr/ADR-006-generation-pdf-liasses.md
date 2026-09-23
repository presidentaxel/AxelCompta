# ADR-006 — Génération PDF des liasses fiscales (fidèle CERFA)

**Date :** 2026-06-16
**Statut :** overlay retenu pour le 2065 et le 2033-A à G (2026-09-23, voir
§Extension au 2033) ; reste à évaluer pour le 2050-2059 et le 2031.
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
- [x] Télécharger et vérifier le 2033 (2033-SD millésime 2026, 7 tableaux,
      **pas d'AcroForm** non plus) : `filings/cerfa/2033-sd_2026.pdf`.
      2050 et 2031 : pas faits.
- [x] POC sur un formulaire à tableaux denses : le 2033 complet (environ
      340 cases numérotées), voir §Extension au 2033.
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

**Complété le même jour** suite à « il me faut tout sur le dossier » (Louis) :
exercice ouvert/clos, régime réel normal, comptabilité informatisée (OUI +
logiciel) rejoignent le résultat fiscal — 4 cases au lieu d'une, toutes des
faits réels (pas d'invention). **Cadre A (désignation de la société, SIRET,
adresse) reste blanc, décision explicite** : aucune identité d'entreprise
n'est modélisée dans le domaine (`tenants/models.py`), et un vrai dossier
historique est pseudonymisé exprès à l'audit (doc 07 §2.2) — y écrire un nom
ou un SIRET serait fabriquer une donnée d'identité, pas en afficher une
vraie. Si une vraie identité de dossier existe un jour (V1), cette case se
remplit alors normalement.

## Extension au 2033 (2026-09-23)

Demande de Louis : une liasse « complète, on ne skip rien ». Le 2033-SD
2026 n'a pas d'AcroForm, donc overlay, comme le 2065. Ce qui change par
rapport au POC : les coordonnées ne sont plus relevées à la main case par
case. Chaque code de case (« 084 », « 310 »...) est imprimé dans une petite
cellule bordée, et la zone de saisie est la cellule suivante à droite ;
`backend/scripts/extraire_cases_cerfa.py` lit ces bordures (pdfplumber) et
écrit `filings/cerfa/cases_2033-sd_2026.json`. Un nombre à trois chiffres
qui n'est pas encadré serré (« art. 302 septies ») est écarté. Une seule
case n'est pas du texte sur ce millésime (460, dessinée en vectoriel) : elle
est déduite de sa ligne et de sa colonne, et c'est écrit dans le script.

Seuls les en-têtes (désignation, SIREN, dates en cases, « Néant ») restent
positionnés à la main dans `filings/cerfa_2033.py`.

Garde-fous : un test vérifie que chaque case calculée par la clôture a une
coordonnée sur le formulaire (sinon elle disparaîtrait du PDF sans erreur),
et le rendu a été relu à l'œil page par page sur les trois dossiers de
démo. À chaque nouveau millésime : télécharger le PDF, relancer le script,
relire le rendu. Le risque noté plus haut reste entier : un décalage de mise
en page ne lève aucune erreur.
