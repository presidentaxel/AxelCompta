"""Factory FastAPI — pas de routes enregistrées à ce stade (squelette).

Démo (doc 17 §6) : minimal, pas prioritaire avant semaine 4, pas d'auth/MFA.
V1 (doc 12) : auth/MFA, permissions par rôle, isolation multi-tenant.
"""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Aucune route enregistrée — à faire une fois les façades des modules
    métier (ledger/service.py, closing/service.py...) écrites."""
    return FastAPI(title="AxeLCompta API", version="0.0.1")
