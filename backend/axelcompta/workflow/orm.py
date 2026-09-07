"""Mapping SQLAlchemy Core de `DecisionHumaine`/`AnnotationDev` (doc 17 §9
bloc A). Défini séparément de `decisions.py` : le domaine reste pur (doc 08
§2.1), seul `decisions_postgres.py` fait de l'I/O contre ces tables.

Append-only par construction : ni l'une ni l'autre table n'a de colonne
mise à jour en place, `enregistrer_decision`/`enregistrer_annotation` ne
font que des `INSERT` (doc 06 §1, même logique que `ledger/orm.py`).

**Pas de `ForeignKey` vers `dossiers`/`ecritures`, contrairement à
`ledger/orm.py`** : pour la démo, dossiers et écritures restent recalculés
à la volée en mémoire (`demo_chauffeurs_type.py`), jamais écrits en
Postgres — seules les décisions humaines et leurs annotations doivent
survivre entre deux requêtes (doc 17 §9 bloc A). Contraindre une FK contre
des tables jamais peuplées ferait échouer tout `INSERT`. À revoir quand
dossiers/écritures seront eux aussi persistés (V1).
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, String, Table

from axelcompta.core.db import metadata

decisions_humaines = Table(
    "decisions_humaines",
    metadata,
    Column("id", String, primary_key=True),
    Column("dossier_id", String, nullable=False),
    Column("ecriture_id", String, nullable=False),
    Column("categorie", String, nullable=False),
    Column("etage_origine", String, nullable=False),
    Column("confiance_origine", Float, nullable=False),
    Column("decide_par", String, nullable=False),
    Column("decide_le", DateTime, nullable=False),
)

annotations_dev = Table(
    "annotations_dev",
    metadata,
    Column("id", String, primary_key=True),
    Column("dossier_id", String, nullable=False),
    Column("ecriture_id", String, nullable=False),
    Column("juste", Boolean, nullable=False),
    Column("note", String, nullable=False),
    Column("annote_par", String, nullable=False),
    Column("annote_le", DateTime, nullable=False),
)
