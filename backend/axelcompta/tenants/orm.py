"""Mapping SQLAlchemy Core de `Dossier` (doc 03 §3bis). Un seul schéma pour
la démo (doc 17 §3) — pas de colonnes RLS/tenant d'isolation ici, la V1 les
ajoutera (doc 03 §7).
"""

from __future__ import annotations

from sqlalchemy import Column, String, Table

from axelcompta.core.db import metadata

dossiers = Table(
    "dossiers",
    metadata,
    Column("id", String, primary_key=True),
    Column("tenant_id", String, nullable=False),
    Column("forme_juridique", String, nullable=False),
    Column("regime_imposition", String, nullable=False),
    Column("regime_tva", String, nullable=False),
)
