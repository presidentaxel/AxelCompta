"""Implémentation Postgres de AvenantRegimeRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine

from axelcompta.core.ids import DossierId
from axelcompta.core.rls import appliquer_rls

from .avenants import AvenantRegime, AvenantRegimeRepository, MotifAvenant
from .orm import avenants_regime as table
from .statuts import RegimeImposition


class PostgresAvenantRegimeRepository(AvenantRegimeRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enregistrer(self, avenant: AvenantRegime) -> None:
        with self._engine.begin() as connexion:
            appliquer_rls(connexion)
            connexion.execute(
                table.insert().values(
                    id=avenant.id,
                    dossier_id=avenant.dossier_id,
                    exercice_effet=avenant.exercice_effet,
                    regime_imposition=avenant.regime_imposition.value,
                    option_ir_debut=avenant.option_ir_debut,
                    motif=avenant.motif.value,
                    enregistre_le=avenant.enregistre_le,
                    enregistre_par=avenant.enregistre_par,
                )
            )

    def lister(self, dossier_id: DossierId) -> tuple[AvenantRegime, ...]:
        with self._engine.connect() as connexion:
            appliquer_rls(connexion)
            lignes = connexion.execute(
                select(table)
                .where(table.c.dossier_id == dossier_id)
                .order_by(table.c.exercice_effet, table.c.enregistre_le)
            ).all()
        return tuple(
            AvenantRegime(
                id=ligne.id,
                dossier_id=DossierId(ligne.dossier_id),
                exercice_effet=ligne.exercice_effet,
                regime_imposition=RegimeImposition(ligne.regime_imposition),
                option_ir_debut=ligne.option_ir_debut,
                motif=MotifAvenant(ligne.motif),
                enregistre_le=ligne.enregistre_le,
                enregistre_par=ligne.enregistre_par,
            )
            for ligne in lignes
        )
