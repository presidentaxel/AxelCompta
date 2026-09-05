"""workflow — validation, revue humaine, signature électronique (doc 05 §5).

Seul module autorisé à transformer une ProposedEntry en écriture réelle via
ledger, après validation (doc 03 §3). Non prévu pour la démo (doc 17 §3) —
dossier présent pour la V1, vide de code pour l'instant. Dépend de core,
categorize, ledger.
"""

from __future__ import annotations
