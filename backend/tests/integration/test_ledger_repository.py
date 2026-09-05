"""PostgresLedgerService contre un vrai Postgres (doc 09 §4, doc 17 semaine 0)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import insert
from sqlalchemy.engine import Engine

from axelcompta.core.db import metadata
from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.tenants.orm import dossiers

pytestmark = pytest.mark.integration


def _dossier_bidon(engine: Engine, dossier_id: str) -> None:
    metadata.create_all(engine)
    with engine.begin() as connexion:
        connexion.execute(
            insert(dossiers).values(
                id=dossier_id,
                tenant_id="t1",
                forme_juridique="SASU",
                regime_imposition="IS",
                regime_tva="reel_normal",
            )
        )


def test_enregistrer_puis_relire_reproduit_le_golden_test_doc17(
    engine: Engine, id_unique: str
) -> None:
    _dossier_bidon(engine, id_unique)
    service = PostgresLedgerService(engine)
    service.enregistrer(
        Ecriture(
            id=EcritureId(f"{id_unique}-e1"),
            dossier_id=DossierId(id_unique),
            journal=Journal.BQ,
            date=date(2026, 9, 3),
            libelle="Règlement Uber (golden test doc 17 §7)",
            reference_piece=None,
            lignes=(
                LigneEcriture(compte="512", sens=Sens.DEBIT, montant=Money(848_00)),
                LigneEcriture(compte="706", sens=Sens.CREDIT, montant=Money(848_00)),
            ),
        )
    )
    grand_livre = service.grand_livre(DossierId(id_unique))
    assert len(grand_livre) == 1
    lignes_lues = {
        (ligne.compte, ligne.sens.name, ligne.montant.centimes) for ligne in grand_livre[0].lignes
    }
    assert lignes_lues == {("512", "DEBIT", 848_00), ("706", "CREDIT", 848_00)}


def test_grand_livre_dun_dossier_inconnu_est_vide(engine: Engine, id_unique: str) -> None:
    metadata.create_all(engine)
    assert PostgresLedgerService(engine).grand_livre(DossierId(id_unique)) == ()
