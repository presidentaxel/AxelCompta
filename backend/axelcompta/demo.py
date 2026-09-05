"""Composition root de la démo doc 17 semaine 0.

Pas un module d'architecture (absent du découpage doc 03 §3) : juste le
point d'entrée qui câble les bouchons ensemble — réconciliation → écriture
→ clôture → PDF. Peut donc importer tous les modules métier sans violer les
règles de dépendance (celles-ci s'appliquent entre modules, pas depuis la
racine de composition, au même titre que `api/`).

Usage : `python -m axelcompta.demo` depuis backend/, une fois le package
installé (`pip install -e .`).
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from axelcompta.closing.bouchon import BouchonClosingService
from axelcompta.core.ids import DossierId, EcritureId, TenantId
from axelcompta.core.money import Money
from axelcompta.filings.pdf_bouchon import PdfBouchonRenderer
from axelcompta.ingestion.providers.base import NormalizedTransaction, PlatformSettlement
from axelcompta.ingestion.providers.fixture import FixtureProvider, FixtureSettlementProvider
from axelcompta.ingestion.reconciliation import reconcilier_bouchon
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

DOSSIER_DEMO = DossierId("demo-1")
TENANT_DEMO = TenantId("demo")
SORTIE_PDF_DEFAUT = Path(__file__).resolve().parent.parent / "_demo_output" / "liasse_semaine0.pdf"


def construire_ecriture_bouchon(
    transaction: NormalizedTransaction, settlement: PlatformSettlement, numero: int
) -> Ecriture:
    """512/706 brut, sans ventilation TVA — le « mode dégradé » que doc 13 §6
    exclut pour la vraie démo, acceptable ici puisque semaine 0 ne vise que
    la couture, pas la justesse (ventilation réelle : semaine 2, doc 13 §5.3).
    """
    montant = Money(centimes=transaction.montant_cts)
    return Ecriture(
        id=EcritureId(f"demo-{numero}"),
        dossier_id=transaction.dossier_id,
        journal=Journal.BQ,
        date=transaction.date,
        libelle=f"Règlement {settlement.platform} (bouchon, sans ventilation TVA)",
        reference_piece=None,
        lignes=(
            LigneEcriture(compte="512", sens=Sens.DEBIT, montant=montant),
            LigneEcriture(compte="706", sens=Sens.CREDIT, montant=montant),
        ),
    )


async def _recuperer_fixtures() -> tuple[
    tuple[NormalizedTransaction, ...], tuple[PlatformSettlement, ...]
]:
    depuis, jusqua = date(2026, 8, 1), date(2026, 9, 30)
    transactions = await FixtureProvider().fetch_transactions(
        TENANT_DEMO, DOSSIER_DEMO, depuis, jusqua
    )
    settlements = await FixtureSettlementProvider().fetch_platform_settlements(
        TENANT_DEMO, DOSSIER_DEMO, depuis, jusqua
    )
    return tuple(transactions), tuple(settlements)


def executer(chemin: Path | None = None) -> Path:
    """Le cœur de la coupe verticale (doc 17 §2). Renvoie le chemin du PDF
    produit ; `chemin` est paramétrable pour rester testable sans écrire
    dans un emplacement fixe du disque à chaque run de test.
    """
    destination = chemin or SORTIE_PDF_DEFAUT
    transactions, settlements = asyncio.run(_recuperer_fixtures())
    paires = reconcilier_bouchon(transactions, settlements)

    ledger = InMemoryLedgerService()
    for numero, (transaction, settlement) in enumerate(paires, start=1):
        ledger.enregistrer(construire_ecriture_bouchon(transaction, settlement, numero))

    liasse = BouchonClosingService(ledger).cloturer(DOSSIER_DEMO, exercice="2026")
    pdf = PdfBouchonRenderer().rendre(liasse)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
    return destination


def main() -> None:
    chemin = executer()
    print(f"Liasse démo générée : {chemin}")


if __name__ == "__main__":
    main()
