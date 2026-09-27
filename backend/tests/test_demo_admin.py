"""Remise à neuf de la démo : les parties proposées et le refus des autres.
L'effacement lui-même est testé sur un vrai Postgres
(`tests/integration/test_demo_admin_postgres.py`)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine

from axelcompta.core.ids import TenantId
from axelcompta.demo_admin import (
    _DOSSIERS_DIGIFACTORY,
    _DOSSIERS_DU_TENANT,
    CLES_PARTIES,
    PARTIES,
    reinitialiser_demo,
)


def test_la_remise_a_neuf_epargne_les_dossiers_digifactory() -> None:
    assert "contact_nr IS NULL" in _DOSSIERS_DU_TENANT


def test_leurs_decisions_ont_une_partie_a_part() -> None:
    """Rejouer « tout confirmer » sur un dossier réel sans toucher à ses
    opérations : une partie distincte, jamais cochée avec les autres."""
    assert "decisions_digifactory" in CLES_PARTIES
    assert "contact_nr IS NOT NULL" in _DOSSIERS_DIGIFACTORY


def test_le_grand_livre_nest_jamais_une_partie() -> None:
    assert CLES_PARTIES == {
        "decisions",
        "decisions_digifactory",
        "jalons",
        "justificatifs",
        "rappels",
        "notifications",
        "portefeuille",
    }
    assert all(partie.libelle and partie.detail for partie in PARTIES)


def test_une_partie_inconnue_est_refusee_avant_toute_connexion(tmp_path: Path) -> None:
    # Moteur jamais connecté : l'erreur doit tomber avant la première requête.
    moteur = create_engine("postgresql+psycopg2://personne@127.0.0.1:1/aucune")

    with pytest.raises(ValueError, match="ecritures"):
        reinitialiser_demo(moteur, TenantId("T"), frozenset({"ecritures"}), tmp_path)
