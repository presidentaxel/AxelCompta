"""Composition root : démo sur un vrai dossier complet, pas un exemple à
2-3 lignes.

Reformulé par Louis (2026-09-05) : le but de la démo, c'est de pouvoir dire
« on peut le faire » — que la chaîne se comporte comme en production,
bout-en-bout, sans viser la perfection sur chaque écriture ni tous les cas
limites (doc 17 §2, §3). Mais le résultat doit **ressembler à un produit**,
donc testé sur un dossier assez complet pour être crédible.

Rejoue une année entière d'un vrai dossier
(`_AUDIT_DONNEES/resultats/fec_ml_taxonomie.csv`, chemin C doc 17 §4) via
`FileImportProvider`. Pas de settlement Rollee ici (aucune donnée Rollee
historique n'existe pour ce dossier) : toutes les transactions passent par
`categorize` + `workflow/auto_accept` — le chemin « reste des
transactions », sans ventilation TVA plateforme. C'est une simplification
assumée, pas un oubli (doc 17 §3).

Comme `demo.py` : pas un module d'architecture (doc 03 §3), composition root.

Usage : `python -m axelcompta.demo_dossier_reel` depuis backend/.
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from axelcompta.categorize.ml_fallback import ModeleMlIndisponible, ModeleSklearn, charger_modele
from axelcompta.categorize.rules_and_ml import RulesAndMlPipeline
from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId, TenantId
from axelcompta.filings.cerfa_2065 import PdfCerfa2065Renderer
from axelcompta.filings.export_comptable import exporter_balance, exporter_grand_livre
from axelcompta.filings.fec import exporter_fec
from axelcompta.filings.liasse_simplifiee import PdfLiasseSimplifieeRenderer
from axelcompta.ingestion.providers.base import NormalizedTransaction
from axelcompta.ingestion.providers.file_import import FileImportProvider
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.packs.vtc_demo import charger_compte_par_categorie, charger_regles
from axelcompta.workflow.auto_accept import construire_ecriture_categorisee

TENANT_DEMO = TenantId("demo")
# 543 transactions réelles reconstruites, 20 catégories, exercice 2024
# complet (01/01 au 31/12) — choisi pour sa richesse, pas trié sur le volet.
DOSSIER_PAR_DEFAUT = DossierId("DOS_98279ecabf05")
ANNEE_PAR_DEFAUT = 2024
DOSSIER_SORTIE_DEFAUT = Path(__file__).resolve().parent.parent / "_demo_output"
SORTIE_PDF_DEFAUT = DOSSIER_SORTIE_DEFAUT / "liasse_dossier_reel.pdf"
SORTIE_CERFA_DEFAUT = DOSSIER_SORTIE_DEFAUT / "cerfa_2065_dossier_reel.pdf"


def _charger_modele_ou_rien() -> ModeleSklearn | None:
    """Dégradation explicite si le modèle .joblib est absent (gitignoré) —
    pas un plantage (doc 08 §5)."""
    try:
        return charger_modele()
    except ModeleMlIndisponible:
        return None


async def _recuperer_transactions(
    dossier_id: DossierId, annee: int
) -> tuple[NormalizedTransaction, ...]:
    depuis, jusqua = date(annee, 1, 1), date(annee, 12, 31)
    return tuple(
        await FileImportProvider().fetch_transactions(TENANT_DEMO, dossier_id, depuis, jusqua)
    )


def construire_ledger(
    dossier_id: DossierId = DOSSIER_PAR_DEFAUT, annee: int = ANNEE_PAR_DEFAUT
) -> InMemoryLedgerService:
    """Cœur réutilisable : ingestion réelle → catégorisation → écritures.
    Partagé par les renderers ci-dessous et par `demo_multi_dossiers.py`
    (doc 17 semaine 4) pour ne pas dupliquer le pipeline une troisième fois.
    """
    transactions = asyncio.run(_recuperer_transactions(dossier_id, annee))

    ledger = InMemoryLedgerService()
    pipeline = RulesAndMlPipeline(regles=charger_regles(), modele=_charger_modele_ou_rien())
    comptes = charger_compte_par_categorie()
    for numero, transaction in enumerate(transactions, start=1):
        proposition = pipeline.categoriser(dossier_id, transaction)
        compte = comptes.get(proposition.categorie, "471")  # 471 : compte d'attente par défaut
        ledger.enregistrer(
            construire_ecriture_categorisee(transaction, proposition, compte, numero)
        )
    return ledger


def construire_liasse(
    dossier_id: DossierId = DOSSIER_PAR_DEFAUT, annee: int = ANNEE_PAR_DEFAUT
) -> LiassePivot:
    ledger = construire_ledger(dossier_id, annee)
    return ClotureSimplifieeService(ledger).cloturer(dossier_id, exercice=str(annee))


def executer(chemin: Path | None = None) -> Path:
    destination = chemin or SORTIE_PDF_DEFAUT
    pdf = PdfLiasseSimplifieeRenderer().rendre(construire_liasse())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
    return destination


def executer_cerfa_2065(chemin: Path | None = None) -> Path:
    """Sur ce dossier de démo, le résultat est négatif : montre la case
    Déficit du vrai formulaire, jamais exercée par le golden test Uber."""
    destination = chemin or SORTIE_CERFA_DEFAUT
    pdf = PdfCerfa2065Renderer().rendre(construire_liasse())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
    return destination


def executer_exports_comptables(
    dossier_id: DossierId = DOSSIER_PAR_DEFAUT,
    annee: int = ANNEE_PAR_DEFAUT,
    dossier_sortie: Path | None = None,
) -> tuple[Path, Path, Path]:
    """FEC + grand livre + balance (doc 06 §6) sur un vrai dossier — le
    détail complet, pas juste le résultat de la liasse (doc 17, suite à
    « s'il est faux, on ne sait pas »)."""
    dossier_sortie = dossier_sortie or DOSSIER_SORTIE_DEFAUT
    ecritures = construire_ledger(dossier_id, annee).grand_livre(dossier_id)
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    chemin_fec = dossier_sortie / "journal_dossier_reel.fec.txt"
    chemin_grand_livre = dossier_sortie / "grand_livre_dossier_reel.csv"
    chemin_balance = dossier_sortie / "balance_dossier_reel.csv"
    chemin_fec.write_text(exporter_fec(ecritures), encoding="utf-8")
    chemin_grand_livre.write_text(exporter_grand_livre(ecritures), encoding="utf-8")
    chemin_balance.write_text(exporter_balance(ecritures), encoding="utf-8")
    return chemin_fec, chemin_grand_livre, chemin_balance


def main() -> None:
    chemin = executer()
    chemin_cerfa = executer_cerfa_2065()
    chemin_fec, chemin_gl, chemin_balance = executer_exports_comptables()
    print(f"Liasse sur dossier réel ({DOSSIER_PAR_DEFAUT}, exercice {ANNEE_PAR_DEFAUT}) : {chemin}")
    print(f"CERFA 2065 (case déficit remplie) : {chemin_cerfa}")
    print(f"FEC : {chemin_fec}")
    print(f"Grand livre : {chemin_gl}")
    print(f"Balance : {chemin_balance}")


if __name__ == "__main__":
    main()
