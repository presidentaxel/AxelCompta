"""Implémentation Postgres de ExerciceRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from axelcompta.core.ids import DossierId
from axelcompta.core.rls import appliquer_rls

from .exercices import ExerciceClos, ExerciceDejaClos, ExerciceRepository
from .orm import exercices_clos as table


class PostgresExerciceRepository(ExerciceRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enregistrer(self, exercice: ExerciceClos) -> None:
        try:
            with self._engine.begin() as connexion:
                appliquer_rls(connexion)
                connexion.execute(
                    table.insert().values(
                        dossier_id=exercice.dossier_id,
                        debut=exercice.debut,
                        fin=exercice.fin,
                        clos_le=exercice.clos_le,
                        clos_par=exercice.clos_par,
                        changements=list(exercice.changements),
                    )
                )
        except IntegrityError as exc:
            message = f"{exercice.dossier_id} : exercice {exercice.debut} déjà clos"
            raise ExerciceDejaClos(message) from exc

    def lister(self, dossier_id: DossierId) -> tuple[ExerciceClos, ...]:
        with self._engine.connect() as connexion:
            appliquer_rls(connexion)
            lignes = connexion.execute(
                select(table).where(table.c.dossier_id == dossier_id).order_by(table.c.debut)
            ).all()
        return tuple(
            ExerciceClos(
                dossier_id=DossierId(ligne.dossier_id),
                debut=ligne.debut,
                fin=ligne.fin,
                clos_le=ligne.clos_le,
                clos_par=ligne.clos_par,
                changements=tuple(ligne.changements),
            )
            for ligne in lignes
        )
