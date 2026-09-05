from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import pytest

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.ingestion.providers.file_import import (
    CSV_AUDIT_PAR_DEFAUT,
    FileImportProvider,
    charger_transactions_csv,
)

ENTETE = (
    "dossier_id,piece_ref,date,libelle_bancaire,montant,"
    "compte_pcg_nature,categorie,type_transaction\n"
)


def _ecrire_csv(tmp_path: Path, lignes: str) -> Path:
    chemin = tmp_path / "audit.csv"
    chemin.write_text(ENTETE + lignes, encoding="utf-8")
    return chemin


def test_transaction_simple_inverse_le_signe_fec(tmp_path: Path) -> None:
    # compte 7060 (produit) débit-crédit négatif = argent reçu -> positif en
    # relevé bancaire (vérifié sur un exemple réel, voir file_import.py).
    csv = _ecrire_csv(
        tmp_path,
        "DOS_1,ENC-001,2026-09-03,VIR RECU UBER,-848.00,7060,recettes_plateformes,simple\n",
    )
    transactions = charger_transactions_csv(
        csv, DossierId("DOS_1"), date(2026, 8, 1), date(2026, 9, 30)
    )
    assert len(transactions) == 1
    assert transactions[0].montant_cts == 848_00
    assert transactions[0].libelle == "VIR RECU UBER"


def test_lignes_composites_sont_regroupees_et_sommees(tmp_path: Path) -> None:
    csv = _ecrire_csv(
        tmp_path,
        "DOS_1,PAI-185#0,2026-09-03,Multiples Comptes - PAI-185,102.26,"
        "6278,frais_bancaires,composite\n"
        "DOS_1,PAI-185#1,2026-09-03,Multiples Comptes - PAI-185,700.00,"
        "6226,honoraires,composite\n",
    )
    transactions = charger_transactions_csv(
        csv, DossierId("DOS_1"), date(2026, 8, 1), date(2026, 9, 30)
    )
    assert len(transactions) == 1
    assert transactions[0].montant_cts == -80_226  # inversé : paiement = sortie d'argent
    lignes_fec = transactions[0].raw_payload["lignes_fec"]
    assert isinstance(lignes_fec, list)
    assert len(lignes_fec) == 2


def test_filtre_par_dossier_et_par_fenetre_de_date(tmp_path: Path) -> None:
    csv = _ecrire_csv(
        tmp_path,
        "DOS_1,ENC-001,2026-09-03,A,-100.00,7060,recettes_plateformes,simple\n"
        "DOS_2,ENC-002,2026-09-03,B,-100.00,7060,recettes_plateformes,simple\n"
        "DOS_1,ENC-003,2020-01-01,C,-100.00,7060,recettes_plateformes,simple\n",
    )
    transactions = charger_transactions_csv(
        csv, DossierId("DOS_1"), date(2026, 8, 1), date(2026, 9, 30)
    )
    assert [t.libelle for t in transactions] == ["A"]


def test_file_import_provider_utilise_le_chemin_injecte(tmp_path: Path) -> None:
    csv = _ecrire_csv(tmp_path, "DOS_1,ENC-001,2026-09-03,A,-100.00,7060,recettes,simple\n")
    provider = FileImportProvider(chemin_csv=csv)
    transactions = asyncio.run(
        provider.fetch_transactions(
            TenantId("t1"), DossierId("DOS_1"), date(2026, 8, 1), date(2026, 9, 30)
        )
    )
    assert len(transactions) == 1


def test_health_signale_un_fichier_absent(tmp_path: Path) -> None:
    provider = FileImportProvider(chemin_csv=tmp_path / "inexistant.csv")
    sante = asyncio.run(provider.health())
    assert sante.ok is False


@pytest.mark.skipif(
    not CSV_AUDIT_PAR_DEFAUT.is_file(),
    reason="CSV audit non présent sur ce poste (gitignored, _AUDIT_DONNEES/resultats/)",
)
def test_contre_le_vrai_csv_audit_si_present() -> None:
    # Sanity-check sur les vraies données (36 152 lignes, doc 17 §4bis) quand
    # elles sont disponibles localement — pas de valeur figée dans le CSV lui
    # même, on vérifie juste que le pipeline tient sur un vrai dossier.
    transactions = charger_transactions_csv(
        CSV_AUDIT_PAR_DEFAUT, DossierId("DOS_2e687acc0d7f"), date(2017, 1, 1), date(2025, 12, 31)
    )
    assert len(transactions) > 0
    assert all(isinstance(t.montant_cts, int) for t in transactions)
