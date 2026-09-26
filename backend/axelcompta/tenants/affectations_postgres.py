"""Implémentation Postgres de AffectationRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from axelcompta.core.ids import DossierId, UserId
from axelcompta.core.rls import appliquer_rls
from axelcompta.workflow.audit import noter

from .affectations import AffectationDejaDecidee, AffectationRepository, DecisionAffectation
from .orm import affectations_resultat as table

TYPE_ACTE_AFFECTATION = "affectation_resultat"


class PostgresAffectationRepository(AffectationRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enregistrer(self, decision: DecisionAffectation) -> None:
        try:
            with self._engine.begin() as connexion:
                appliquer_rls(connexion)
                connexion.execute(
                    table.insert().values(
                        dossier_id=decision.dossier_id,
                        annee_exercice=decision.annee_exercice,
                        scenario=decision.scenario,
                        dividendes_cts=decision.dividendes_cts,
                        reserve_legale_cts=decision.reserve_legale_cts,
                        decide_le=decision.decide_le,
                        decide_par=decision.decide_par,
                    )
                )
                # Même transaction : pas de décision sans sa trace, ni l'inverse.
                noter(
                    connexion,
                    decision.dossier_id,
                    TYPE_ACTE_AFFECTATION,
                    f"exercice:{decision.annee_exercice}",
                    UserId(decision.decide_par),
                    decision.decide_le,
                )
        except IntegrityError as exc:
            message = f"{decision.dossier_id} : exercice {decision.annee_exercice} déjà affecté"
            raise AffectationDejaDecidee(message) from exc

    def obtenir(self, dossier_id: DossierId, annee_exercice: int) -> DecisionAffectation | None:
        with self._engine.connect() as connexion:
            appliquer_rls(connexion)
            ligne = connexion.execute(
                select(table).where(
                    table.c.dossier_id == dossier_id, table.c.annee_exercice == annee_exercice
                )
            ).first()
        if ligne is None:
            return None
        return DecisionAffectation(
            dossier_id=DossierId(ligne.dossier_id),
            annee_exercice=ligne.annee_exercice,
            scenario=ligne.scenario,
            dividendes_cts=ligne.dividendes_cts,
            reserve_legale_cts=ligne.reserve_legale_cts,
            decide_le=ligne.decide_le,
            decide_par=ligne.decide_par,
        )
