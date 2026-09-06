"""Composition root de la démo doc 17 (semaines 0-3).

Pas un module d'architecture (absent du découpage doc 03 §3) : juste le
point d'entrée qui câble les briques ensemble — réconciliation → écriture
(settlement plateforme avec ventilation TVA réelle, ou catégorisation
règles/ML pour le reste) → clôture simplifiée → liasse PDF simplifiée. Peut
donc importer tous les modules métier sans violer les règles de dépendance
(celles-ci s'appliquent entre modules, pas depuis la racine de composition,
au même titre qu'`api/`).

Usage : `python -m axelcompta.demo` depuis backend/, une fois le package
installé (`pip install -e .`).
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from axelcompta.categorize.ml_fallback import ModeleMlIndisponible, ModeleSklearn, charger_modele
from axelcompta.categorize.rules_and_ml import RulesAndMlPipeline
from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId, TenantId, TransactionId
from axelcompta.filings.cerfa_2065 import PdfCerfa2065Renderer
from axelcompta.filings.export_comptable import exporter_balance, exporter_grand_livre
from axelcompta.filings.fec import exporter_fec
from axelcompta.filings.liasse_simplifiee import PdfLiasseSimplifieeRenderer
from axelcompta.ingestion.ecritures_settlement import construire_ecriture_settlement
from axelcompta.ingestion.providers.base import NormalizedTransaction, PlatformSettlement
from axelcompta.ingestion.providers.fixture import FixtureProvider, FixtureSettlementProvider
from axelcompta.ingestion.reconciliation import EtatReconciliation, reconcilier
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.packs.vtc_demo import charger_compte_par_categorie, charger_regles
from axelcompta.workflow.auto_accept import construire_ecriture_categorisee

DOSSIER_DEMO = DossierId("demo-1")
TENANT_DEMO = TenantId("demo")
DOSSIER_SORTIE_DEFAUT = Path(__file__).resolve().parent.parent / "_demo_output"
SORTIE_PDF_DEFAUT = DOSSIER_SORTIE_DEFAUT / "liasse.pdf"
SORTIE_CERFA_DEFAUT = DOSSIER_SORTIE_DEFAUT / "cerfa_2065.pdf"

# Transactions « reste des transactions » (doc 17 §6, semaine 2) : ne passent
# pas par un settlement Rollee, juste par règles + ML (categorize/). Ajoutées
# ici plutôt que dans FixtureProvider pour ne pas changer son contrat
# (plusieurs tests existants comptent sur son unique transaction golden test).
TRANSACTIONS_SUPPLEMENTAIRES = (
    NormalizedTransaction(
        id=TransactionId("demo-carburant-1"),
        dossier_id=DOSSIER_DEMO,
        date=date(2026, 9, 4),
        montant_cts=-45_00,
        libelle="CB TOTAL ACCESS A6 04/09",
        source_provider="demo",
        raw_payload={},
    ),
    NormalizedTransaction(
        id=TransactionId("demo-peage-1"),
        dossier_id=DOSSIER_DEMO,
        date=date(2026, 9, 5),
        montant_cts=-12_30,
        libelle="COFIROUTE A10",
        source_provider="demo",
        raw_payload={},
    ),
)


def _charger_modele_ou_rien() -> ModeleSklearn | None:
    """Dégradation explicite si le modèle .joblib est absent (gitignoré) —
    pas un plantage (doc 08 §5)."""
    try:
        return charger_modele()
    except ModeleMlIndisponible:
        return None


async def _recuperer_fixtures() -> tuple[
    tuple[NormalizedTransaction, ...],
    tuple[PlatformSettlement, ...],
]:
    depuis, jusqua = date(2026, 8, 1), date(2026, 9, 30)
    transactions_uber = await FixtureProvider().fetch_transactions(
        TENANT_DEMO, DOSSIER_DEMO, depuis, jusqua
    )
    settlements = await FixtureSettlementProvider().fetch_platform_settlements(
        TENANT_DEMO, DOSSIER_DEMO, depuis, jusqua
    )
    transactions = tuple(transactions_uber) + TRANSACTIONS_SUPPLEMENTAIRES
    return transactions, tuple(settlements)


def _construire_ledger() -> InMemoryLedgerService:
    """Le cœur de la coupe verticale (doc 17 §2) : fixtures → réconciliation
    → écritures. Partagé par les renderers de liasse (qui clôturent) et les
    exports comptables (qui lisent directement le grand livre, doc 06 §6).
    """
    transactions, settlements = asyncio.run(_recuperer_fixtures())
    resultats = reconcilier(transactions, settlements)

    ledger = InMemoryLedgerService()
    id_transactions_reconciliees = {
        r.transaction.id for r in resultats if r.transaction is not None
    }
    for numero, resultat in enumerate(resultats, start=1):
        if resultat.etat is EtatReconciliation.RECONCILIE and resultat.transaction is not None:
            ecriture = construire_ecriture_settlement(
                resultat.transaction, resultat.settlement, numero
            )
            ledger.enregistrer(ecriture)

    pipeline = RulesAndMlPipeline(regles=charger_regles(), modele=_charger_modele_ou_rien())
    comptes = charger_compte_par_categorie()
    for numero, transaction in enumerate(transactions, start=1):
        if transaction.id in id_transactions_reconciliees:
            continue
        proposition = pipeline.categoriser(DOSSIER_DEMO, transaction)
        compte = comptes.get(proposition.categorie, "471")  # 471 : compte d'attente par défaut
        ledger.enregistrer(
            construire_ecriture_categorisee(transaction, proposition, compte, numero)
        )

    return ledger


def _construire_liasse() -> LiassePivot:
    return ClotureSimplifieeService(_construire_ledger()).cloturer(DOSSIER_DEMO, exercice="2026")


def executer(chemin: Path | None = None) -> Path:
    """Liasse simplifiée (compte de résultat + bilan, doc 17 semaine 3).
    `chemin` est paramétrable pour rester testable sans écrire dans un
    emplacement fixe du disque à chaque run de test.
    """
    destination = chemin or SORTIE_PDF_DEFAUT
    pdf = PdfLiasseSimplifieeRenderer().rendre(_construire_liasse())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
    return destination


def executer_cerfa_2065(chemin: Path | None = None) -> Path:
    """Overlay sur le vrai formulaire officiel 2065-SD (doc 17 §3, ADR-006) —
    voir `filings/cerfa_2065.py` pour ce qui est rempli et ce qui ne l'est pas."""
    destination = chemin or SORTIE_CERFA_DEFAUT
    pdf = PdfCerfa2065Renderer().rendre(_construire_liasse())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
    return destination


def executer_exports_comptables(dossier_sortie: Path | None = None) -> tuple[Path, Path, Path]:
    """FEC + grand livre + balance (doc 06 §6) — le détail derrière les
    chiffres de la liasse, pour un contrôle ou pour tracer une erreur
    (2026-09-05, suite à « s'il est faux, on ne sait pas »)."""
    dossier_sortie = dossier_sortie or DOSSIER_SORTIE_DEFAUT
    ecritures = _construire_ledger().grand_livre(DOSSIER_DEMO)
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    chemin_fec = dossier_sortie / "journal.fec.txt"
    chemin_grand_livre = dossier_sortie / "grand_livre.csv"
    chemin_balance = dossier_sortie / "balance.csv"
    chemin_fec.write_text(exporter_fec(ecritures), encoding="utf-8")
    chemin_grand_livre.write_text(exporter_grand_livre(ecritures), encoding="utf-8")
    chemin_balance.write_text(exporter_balance(ecritures), encoding="utf-8")
    return chemin_fec, chemin_grand_livre, chemin_balance


def main() -> None:
    chemin = executer()
    chemin_cerfa = executer_cerfa_2065()
    chemin_fec, chemin_gl, chemin_balance = executer_exports_comptables()
    print(f"Liasse démo générée : {chemin}")
    print(f"CERFA 2065 (case résultat fiscal remplie) : {chemin_cerfa}")
    print(f"FEC : {chemin_fec}")
    print(f"Grand livre : {chemin_gl}")
    print(f"Balance : {chemin_balance}")


if __name__ == "__main__":
    main()
