"""Implémentation Postgres de NotificationRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.rls import appliquer_rls

from .notifications import NotificationEnvoyee, NotificationRepository
from .orm import notifications_envoyees as table


class PostgresNotificationRepository(NotificationRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def derniere(self, dossier_id: DossierId, type_: str) -> NotificationEnvoyee | None:
        with self._engine.connect() as connexion:
            appliquer_rls(connexion)
            ligne = connexion.execute(
                select(table)
                .where(table.c.dossier_id == dossier_id, table.c.type == type_)
                .order_by(table.c.envoye_le.desc())
                .limit(1)
            ).first()
        if ligne is None:
            return None
        return NotificationEnvoyee(
            id=ligne.id,
            dossier_id=DossierId(ligne.dossier_id),
            type=ligne.type,
            envoye_le=ligne.envoye_le,
            ecriture_ids=tuple(EcritureId(i) for i in ligne.ecriture_ids),
        )

    def enregistrer(self, notification: NotificationEnvoyee) -> None:
        with self._engine.begin() as connexion:
            appliquer_rls(connexion)
            connexion.execute(
                table.insert().values(
                    id=notification.id,
                    dossier_id=notification.dossier_id,
                    type=notification.type,
                    envoye_le=notification.envoye_le,
                    ecriture_ids=list(notification.ecriture_ids),
                )
            )
