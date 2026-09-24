"""Tables du journal d'ingestion (doc 12 §1.2 : archivage brut immuable,
quarantaine, reprise incrémentale). Insert-only sauf le curseur, qui ne fait
qu'avancer."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, String, Table

from axelcompta.core.db import metadata

# Tout ce que le fournisseur a renvoyé, tel quel. `id` = empreinte du contenu
# (dossier + source + payload canonique) : rejouer la même ligne ne crée rien,
# et une ligne modifiée côté fournisseur crée une nouvelle entrée sans effacer
# l'ancienne.
ingestion_brut = Table(
    "ingestion_brut",
    metadata,
    Column("id", String, primary_key=True),
    Column("dossier_id", String, ForeignKey("dossiers.id"), nullable=False, index=True),
    Column("source", String, nullable=False),
    Column("transaction_id", String, nullable=True),
    Column("updated_at", String, nullable=True),
    Column("payload", JSON, nullable=False),
    Column("recu_le", DateTime, nullable=False),
)

# Ce qui n'a pas pu être comptabilisé sans jugement humain : ligne illisible,
# transaction modifiée ou supprimée après avoir été comptabilisée. `id` =
# empreinte (dossier, source, motif, payload) : un même cas n'est signalé
# qu'une fois malgré le recouvrement des lectures.
quarantaine_ingestion = Table(
    "quarantaine_ingestion",
    metadata,
    Column("id", String, primary_key=True),
    Column("dossier_id", String, ForeignKey("dossiers.id"), nullable=False, index=True),
    Column("source", String, nullable=False),
    Column("motif", String, nullable=False),
    Column("transaction_id", String, nullable=True),
    Column("payload", JSON, nullable=False),
    Column("mis_en_quarantaine_le", DateTime, nullable=False),
)

# Point de reprise par (dossier, source) : plus grand `updated_at` traité.
curseurs_synchro = Table(
    "curseurs_synchro",
    metadata,
    Column("dossier_id", String, ForeignKey("dossiers.id"), primary_key=True),
    Column("source", String, primary_key=True),
    Column("dernier_updated_at", DateTime, nullable=False),
    Column("maj_le", DateTime, nullable=False),
)

# État courant du consentement DSP2, une ligne par dossier. Ce n'est pas une
# écriture comptable : on remplace le relevé précédent (doc 14 §2.2).
consentements_bancaires = Table(
    "consentements_bancaires",
    metadata,
    Column("dossier_id", String, ForeignKey("dossiers.id"), primary_key=True),
    Column("expire_le", Date, nullable=True),
    Column("statut", String, nullable=False),
    Column("releve_le", DateTime(timezone=True), nullable=False),
)
