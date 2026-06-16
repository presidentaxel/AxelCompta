# ADR-005 — Moteur OCR pour les justificatifs

**Date :** 2026-06-16
**Statut :** en attente de benchmark — décision à prendre en phase 0 (spike OCR)
**Décideurs :** Louis Vedovato

## Contexte

Les justificatifs entrants (tickets de carburant, factures fournisseurs, relevés de péage) doivent être traités pour en extraire : montant TTC, montant HT, taux TVA, date, fournisseur, numéro de pièce. La qualité de l'extraction conditionne la précision du matching justificatif ↔ transaction (doc 04).

## Cascade d'extraction (du moins au plus coûteux)

1. **PDF natif avec texte embarqué** : extraction directe (pdfminer, pypdf). Coût nul. Qualité parfaite si le PDF est généré numériquement (factures Uber, Bolt, fournisseurs professionnels).
2. **Factur-X / UBL** : extraction des champs structurés XML embarqués. Coût nul. Qualité parfaite. À privilégier avec la réforme facturation électronique 2026 (doc 02 §7).
3. **OCR open-source** : sur les images/scans. Candidates : Tesseract (mature, gratuit) et PaddleOCR (meilleure précision sur tickets FR).
4. **Vision LLM** : dernier recours pour les tickets illisibles, recadrés, manuscrits. Coût unitaire élevé, données pseudonymisées avant envoi (doc 10 §4).

## Candidats pour l'étage OCR

| Moteur | Avantages | Inconvénients |
|--------|-----------|--------------|
| Tesseract 5 | Gratuit, mature, bien documenté, self-hosted | Précision limitée sur tickets froissés, petits fonts |
| PaddleOCR | Précision supérieure, multi-langues, self-hosted | Plus lourd à déployer, dépendance Python/C++ |
| Google Vision API | Excellente précision | Données sortent du périmètre, coût à volume |

## Décision à prendre

Le spike phase 0 consiste à tester les 3 moteurs sur 30 tickets réels représentatifs du pilote (carburant, péages, factures LOA) et à mesurer la précision d'extraction des champs clés.

**Critère de décision :** précision extraction `montant_ttc` ≥ 95 % sur le corpus de test. Le gagnant devient le moteur par défaut de l'étage 3.

Google Vision API est exclu par principe (données hors périmètre) sauf si aucune solution self-hosted n'atteint le seuil.

## Action requise

- [ ] Constituer le corpus de 30 tickets réels anonymisés
- [ ] Benchmark Tesseract vs PaddleOCR sur ce corpus
- [ ] Documenter les résultats et mettre à jour cet ADR avec la décision finale
