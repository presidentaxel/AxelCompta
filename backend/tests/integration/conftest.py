"""Fixtures des tests d'intégration (doc 09 §4) : nécessitent un vrai
Postgres — `docker compose up -d db` depuis backend/ (doc 17 semaine 0).
Exclus de la suite rapide par défaut (voir addopts, pyproject.toml).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

# L'import seul enregistre les tables de chaque module sur metadata partagée
# (doc 03 §3) : nécessaire pour que create_all/drop_all les voient.
import axelcompta.ledger.orm  # noqa: F401
import axelcompta.tenants.orm  # noqa: F401
import axelcompta.workflow.orm  # noqa: F401
from axelcompta.core.db import engine_depuis_env, metadata


@pytest.fixture
def engine() -> Iterator[Engine]:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL non définie — voir backend/README.md")
    moteur = engine_depuis_env()
    yield moteur
    metadata.drop_all(moteur)  # nettoyage après chaque test, no-op si rien à supprimer
    # `alembic_version` n'est pas dans `metadata` (bookkeeping propre à
    # Alembic) : sans ce DROP, un test suivant qui utilise Alembic
    # directement (test_migrations.py) croit être déjà à `head` et ne
    # recrée rien — trouvé le 2026-09-08 en enchaînant plusieurs tests
    # d'intégration dans la même session.
    with moteur.begin() as connexion:
        connexion.execute(text("DROP TABLE IF EXISTS alembic_version"))


@pytest.fixture
def id_unique() -> str:
    return uuid.uuid4().hex[:12]
