"""Implémentation Postgres de DossierRepository (seul fichier de `tenants`
qui fait de l'I/O)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from axelcompta.core.ids import DossierId, TenantId

from .models import Dossier, Tenant
from .orm import dossiers, tenants
from .repository import DossierRepository


class PostgresDossierRepository(DossierRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enregistrer_tenant(self, tenant: Tenant) -> None:
        with self._engine.begin() as connexion:
            connexion.execute(
                insert(tenants).values(id=tenant.id, nom=tenant.nom).on_conflict_do_nothing()
            )

    def enregistrer(self, dossier: Dossier) -> None:
        with self._engine.begin() as connexion:
            connexion.execute(
                insert(dossiers)
                .values(
                    id=dossier.id,
                    tenant_id=dossier.tenant_id,
                    forme_juridique=dossier.forme_juridique,
                    regime_imposition=dossier.regime_imposition,
                    regime_tva=dossier.regime_tva,
                    nom=dossier.nom,
                    tva_recettes_regime=dossier.tva_recettes_regime,
                    exercice_debut=dossier.exercice_debut,
                    plateformes=list(dossier.plateformes),
                    mode_acces_bancaire=dossier.mode_acces_bancaire,
                    contact_nr=dossier.contact_nr,
                )
                .on_conflict_do_nothing(index_elements=[dossiers.c.id])
            )

    def obtenir(self, dossier_id: DossierId) -> Dossier | None:
        with self._engine.connect() as connexion:
            ligne = connexion.execute(select(dossiers).where(dossiers.c.id == dossier_id)).first()
        return _vers_dossier(ligne) if ligne is not None else None

    def lister_par_tenant(self, tenant_id: TenantId) -> tuple[Dossier, ...]:
        with self._engine.connect() as connexion:
            lignes = connexion.execute(
                select(dossiers).where(dossiers.c.tenant_id == tenant_id).order_by(dossiers.c.id)
            ).all()
        return tuple(_vers_dossier(ligne) for ligne in lignes)

    def par_contact_nr(self, contact_nr: str) -> Dossier | None:
        with self._engine.connect() as connexion:
            ligne = connexion.execute(
                select(dossiers).where(dossiers.c.contact_nr == contact_nr)
            ).first()
        return _vers_dossier(ligne) if ligne is not None else None


def _vers_dossier(ligne: Any) -> Dossier:
    return Dossier(
        id=DossierId(ligne.id),
        tenant_id=TenantId(ligne.tenant_id),
        forme_juridique=ligne.forme_juridique,
        regime_imposition=ligne.regime_imposition,
        regime_tva=ligne.regime_tva,
        nom=ligne.nom,
        tva_recettes_regime=ligne.tva_recettes_regime,
        exercice_debut=ligne.exercice_debut,
        plateformes=tuple(ligne.plateformes),
        mode_acces_bancaire=ligne.mode_acces_bancaire,
        contact_nr=ligne.contact_nr,
    )
