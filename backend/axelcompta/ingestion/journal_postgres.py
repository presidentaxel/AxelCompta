"""Implémentation Postgres de JournalIngestion."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from axelcompta.core.ids import DossierId

from .journal import EntreeQuarantaine, JournalIngestion, empreinte, maintenant
from .orm import curseurs_synchro, ingestion_brut, quarantaine_ingestion


class PostgresJournalIngestion(JournalIngestion):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def archiver(
        self,
        dossier_id: DossierId,
        source: str,
        transaction_id: str | None,
        updated_at: str | None,
        payload: dict[str, object],
    ) -> None:
        with self._engine.begin() as connexion:
            connexion.execute(
                insert(ingestion_brut)
                .values(
                    id=empreinte(dossier_id, source, payload=payload),
                    dossier_id=dossier_id,
                    source=source,
                    transaction_id=transaction_id,
                    updated_at=updated_at,
                    payload=payload,
                    recu_le=maintenant(),
                )
                .on_conflict_do_nothing(index_elements=[ingestion_brut.c.id])
            )

    def mettre_en_quarantaine(
        self,
        dossier_id: DossierId,
        source: str,
        motif: str,
        transaction_id: str | None,
        payload: dict[str, object],
    ) -> None:
        with self._engine.begin() as connexion:
            connexion.execute(
                insert(quarantaine_ingestion)
                .values(
                    id=empreinte(dossier_id, source, motif, payload=payload),
                    dossier_id=dossier_id,
                    source=source,
                    motif=motif,
                    transaction_id=transaction_id,
                    payload=payload,
                    mis_en_quarantaine_le=maintenant(),
                )
                .on_conflict_do_nothing(index_elements=[quarantaine_ingestion.c.id])
            )

    def lister_quarantaine(self, dossier_id: DossierId) -> tuple[EntreeQuarantaine, ...]:
        with self._engine.connect() as connexion:
            lignes = connexion.execute(
                select(quarantaine_ingestion)
                .where(quarantaine_ingestion.c.dossier_id == dossier_id)
                .order_by(quarantaine_ingestion.c.mis_en_quarantaine_le)
            ).all()
        return tuple(
            EntreeQuarantaine(
                DossierId(ligne.dossier_id),
                ligne.source,
                ligne.motif,
                ligne.transaction_id,
                ligne.payload,
            )
            for ligne in lignes
        )

    def curseur(self, dossier_id: DossierId, source: str) -> datetime | None:
        with self._engine.connect() as connexion:
            return connexion.execute(
                select(curseurs_synchro.c.dernier_updated_at).where(
                    curseurs_synchro.c.dossier_id == dossier_id,
                    curseurs_synchro.c.source == source,
                )
            ).scalar()

    def avancer_curseur(self, dossier_id: DossierId, source: str, valeur: datetime) -> None:
        insertion = insert(curseurs_synchro).values(
            dossier_id=dossier_id, source=source, dernier_updated_at=valeur, maj_le=maintenant()
        )
        with self._engine.begin() as connexion:
            connexion.execute(
                insertion.on_conflict_do_update(
                    index_elements=[curseurs_synchro.c.dossier_id, curseurs_synchro.c.source],
                    set_={"dernier_updated_at": valeur, "maj_le": maintenant()},
                    # Ne recule jamais, même sous deux synchros concurrentes.
                    where=curseurs_synchro.c.dernier_updated_at < valeur,
                )
            )
