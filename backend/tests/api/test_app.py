from __future__ import annotations

from fastapi import FastAPI

from axelcompta.api.app import create_app

ROUTES_FASTAPI_PAR_DEFAUT = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}


def test_create_app_ne_declare_encore_aucune_route() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)
    routes_metier = [
        route for route in app.routes if getattr(route, "path", "") not in ROUTES_FASTAPI_PAR_DEFAUT
    ]
    assert routes_metier == []
