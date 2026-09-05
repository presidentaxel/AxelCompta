"""Vérifie que la migration initiale s'applique et se retire proprement
contre un vrai Postgres (doc 17 semaine 0 : « Postgres + Alembic minimal »).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration

BACKEND = Path(__file__).resolve().parent.parent.parent
TABLES_ATTENDUES = {"dossiers", "ecritures", "lignes_ecriture"}


def _config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    return cfg


def test_upgrade_puis_downgrade_sont_symetriques(engine: Engine) -> None:
    cfg = _config()
    command.upgrade(cfg, "head")
    assert TABLES_ATTENDUES <= set(inspect(engine).get_table_names())

    command.downgrade(cfg, "base")
    assert not (TABLES_ATTENDUES & set(inspect(engine).get_table_names()))
