"""Orchestration multi-dossiers : un dossier en échec ou sans contact ne
bloque pas les autres."""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import date, datetime

from axelcompta.categorize.rules_and_ml import RulesAndMlPipeline
from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.journal import InMemoryJournalIngestion
from axelcompta.ingestion.providers.base import LotTransactions
from axelcompta.ingestion.providers.digifactory import DigifactoryProvider
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.packs.vtc_demo import charger_compte_par_categorie, charger_regles
from axelcompta.synchro_digifactory import synchroniser_dossiers
from axelcompta.tenants.models import Dossier
from axelcompta.workflow.propositions import InMemoryPropositionRepository

BASE = Dossier(
    id=DossierId("a"),
    tenant_id=TenantId("t"),
    forme_juridique="SASU",
    regime_imposition="IS",
    regime_tva="reel_normal",
    nom="A",
    tva_recettes_regime="franchise",
    exercice_debut=date(2026, 1, 1),
    contact_nr="1",
)
PAYLOAD = {
    "acc": [
        {
            "id": "t1",
            "provider_description": "CARTE TOTAL",
            "amount": -10.0,
            "date": "2026-03-01",
            "updated_at": "2026-03-01 10:00:00",
            "deleted": False,
            "future": False,
        }
    ]
}


class _SourceQuiEchoueSurB:
    def __init__(self) -> None:
        self._vraie = DigifactoryProvider(payload=PAYLOAD)

    async def lire_lot(self, dossier: Dossier, depuis_maj: datetime | None) -> LotTransactions:
        if dossier.id == "b":
            raise RuntimeError("Digifactory a répondu 500")
        return await self._vraie.lire_lot(dossier, depuis_maj)


def test_un_dossier_en_echec_ou_sans_contact_ne_bloque_pas_les_autres() -> None:
    dossiers = (
        BASE,
        dataclasses.replace(BASE, id=DossierId("b"), contact_nr="2"),
        dataclasses.replace(BASE, id=DossierId("c"), contact_nr=None),
        dataclasses.replace(BASE, id=DossierId("d"), contact_nr="4"),
    )
    ledger = InMemoryLedgerService()

    resultats = asyncio.run(
        synchroniser_dossiers(
            dossiers,
            _SourceQuiEchoueSurB(),
            InMemoryJournalIngestion(),
            ledger,
            InMemoryPropositionRepository(),
            RulesAndMlPipeline(regles=charger_regles(), modele=None),
            charger_compte_par_categorie(),
        )
    )

    par_id = {r.dossier_id: r for r in resultats}
    resultat_a, resultat_b, resultat_c, resultat_d = (
        par_id[DossierId("a")],
        par_id[DossierId("b")],
        par_id[DossierId("c")],
        par_id[DossierId("d")],
    )
    assert resultat_a.rapport is not None and resultat_a.rapport.nouvelles == 1
    assert resultat_b.erreur is not None and "500" in resultat_b.erreur
    assert resultat_c.ignore is not None
    assert resultat_d.rapport is not None and resultat_d.rapport.nouvelles == 1
    assert len(ledger.grand_livre(DossierId("d"))) == 1
