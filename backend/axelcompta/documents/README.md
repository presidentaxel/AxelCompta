# documents/

Justificatifs : stockage, OCR, Factur-X, matching avec les transactions
bancaires.

**Dépendances :** `core`, `tenants`.

## Contenu prévu (V1)

- Extraction native PDF → OCR open-source (Tesseract/PaddleOCR) → Vision LLM
  en fallback (hybride, doc 04 §4, arbitré par ADR-005).
- Parsing Factur-X.
- Matching justificatif ↔ transaction bancaire.
- Stockage S3-compatible avec versioning + verrouillage WORM (archivage
  légal).

## Statuts

- **Démo (doc 17 §3)** : **non prévu.** Explicitement exclu du scope démo —
  les transactions sont traitées sans matching de pièce.
- **V1 (doc 12, phase 0.3 puis 1-2)** : spike OCR (30 tickets réels, Tesseract
  vs PaddleOCR vs Vision LLM) avant tout développement en profondeur.

## Doc de référence

[doc 04 §4](../../../docs/04-ingestion-donnees.md#4-justificatifs--ocr-vision-factur-x),
[ADR-005](../../../docs/adr/ADR-005-moteur-ocr.md),
[doc 07 §7](../../../docs/07-ml-donnees-entrainement.md#7-ocrvision--évaluation-spécifique).
