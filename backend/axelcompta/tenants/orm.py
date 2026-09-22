"""Mapping SQLAlchemy Core de `Tenant` et `Dossier` (doc 03 §3bis). Un seul
schéma (doc 17 §3) : l'isolation par `tenant_id` se fait dans les requêtes du
repository (`DossierRepository.lister_par_tenant`) ; la RLS Postgres de la V1
(doc 03 §7) reste à faire.
"""

from __future__ import annotations

from sqlalchemy import JSON, Column, Date, ForeignKey, String, Table

from axelcompta.core.db import metadata

tenants = Table(
    "tenants",
    metadata,
    Column("id", String, primary_key=True),
    Column("nom", String, nullable=False),
)

dossiers = Table(
    "dossiers",
    metadata,
    Column("id", String, primary_key=True),
    Column("tenant_id", String, ForeignKey("tenants.id"), nullable=False),
    Column("forme_juridique", String, nullable=False),
    Column("regime_imposition", String, nullable=False),
    Column("regime_tva", String, nullable=False),
    Column("nom", String, nullable=False),
    Column("tva_recettes_regime", String, nullable=False),
    Column("exercice_debut", Date, nullable=False),
    Column("plateformes", JSON, nullable=False),
    Column("mode_acces_bancaire", String, nullable=False),
    # Unique quand renseigné (Postgres autorise plusieurs NULL) : un contact
    # Digifactory ne peut pointer que vers un seul dossier.
    Column("contact_nr", String, nullable=True, unique=True),
)
