"""workflow — validation, revue humaine, signature électronique (doc 05 §5).

Seul module autorisé à transformer une ProposedEntry en écriture réelle via
ledger, après validation (doc 03 §3). La vraie revue humaine reste non
prévue pour la démo (doc 17 §3) : `auto_accept.py` est un stand-in minimal
qui accepte tout sans validation (doc 17 semaine 2). Dépend de core,
categorize, ingestion (types transaction), ledger.
"""

from __future__ import annotations
