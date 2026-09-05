"""ml — entraînement, évaluation, registry de modèles (doc 07).

Hors runtime API : personne n'importe ce module au runtime (règle CI,
doc 03 §3) — les modèles sont chargés comme artefacts (`.joblib`) par
`categorize/`. Non prévu pour la démo (doc 17 §3, §4bis) : le modèle déjà
entraîné dans `_AUDIT_DONNEES/modeles/` est réutilisé tel quel.
"""

from __future__ import annotations
