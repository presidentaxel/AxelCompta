"""Relevé Postgres du consentement bancaire. Une ligne par dossier, remplacée
à chaque synchro : c'est l'état courant, pas une écriture comptable.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from axelcompta.core.ids import DossierId
from axelcompta.core.rls import appliquer_rls

from .consentement import ReleveConsentement, ReleveSante, SanteConnexion, StatutConsentement
from .orm import consentements_bancaires


class PostgresConsentementRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enregistrer(
        self,
        dossier_id: DossierId,
        expire_le: date | None,
        statut: StatutConsentement,
        releve_le: datetime,
        sante: ReleveSante,
    ) -> None:
        with self._engine.begin() as connexion:
            appliquer_rls(connexion)
            valeurs = {
                "expire_le": expire_le,
                "statut": statut.value,
                "releve_le": releve_le,
                "sante": sante.statut.value,
                "en_pause": sante.en_pause,
                "acces_donnees": sante.acces_donnees,
                "dernier_rafraichissement": sante.dernier_rafraichissement,
            }
            connexion.execute(
                insert(consentements_bancaires)
                .values(dossier_id=dossier_id, **valeurs)
                .on_conflict_do_update(
                    index_elements=[consentements_bancaires.c.dossier_id],
                    set_=valeurs,
                )
            )

    def lister(self, dossier_ids: Sequence[DossierId]) -> dict[DossierId, ReleveConsentement]:
        """Les dossiers jamais relevés sont absents du résultat."""
        if not dossier_ids:
            return {}
        with self._engine.connect() as connexion:
            appliquer_rls(connexion)
            lignes = connexion.execute(
                select(consentements_bancaires).where(
                    consentements_bancaires.c.dossier_id.in_(list(dossier_ids))
                )
            ).all()
        return {
            DossierId(ligne.dossier_id): ReleveConsentement(
                dossier_id=DossierId(ligne.dossier_id),
                expire_le=ligne.expire_le,
                sante=SanteConnexion(ligne.sante),
                dernier_rafraichissement=ligne.dernier_rafraichissement,
                releve_le=ligne.releve_le,
            )
            for ligne in lignes
        }
