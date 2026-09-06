from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.filings.fec import COLONNES_FEC, exporter_fec
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

DOSSIER = DossierId("d1")


def _ecriture_uber() -> Ecriture:
    return Ecriture(
        id=EcritureId("e1"),
        dossier_id=DOSSIER,
        journal=Journal.BQ,
        date=date(2026, 9, 3),
        libelle="Règlement Uber",
        reference_piece="PIECE-1",
        lignes=(
            LigneEcriture("512", Sens.DEBIT, Money(848_00)),
            LigneEcriture("706", Sens.CREDIT, Money(945_45)),
            LigneEcriture("44571", Sens.CREDIT, Money(94_55)),
        ),
    )


def test_len_de_lentete_est_les_18_colonnes_normees() -> None:
    assert len(COLONNES_FEC) == 18


def test_exporte_une_ligne_par_ligne_decriture_avec_entete() -> None:
    fec = exporter_fec((_ecriture_uber(),))
    lignes = fec.strip("\n").split("\n")
    assert lignes[0] == "\t".join(COLONNES_FEC)
    assert len(lignes) == 1 + 3  # entête + 3 lignes d'écriture


def test_champs_debit_credit_et_date_correctement_formates() -> None:
    fec = exporter_fec((_ecriture_uber(),))
    lignes = fec.strip("\n").split("\n")[1:]
    par_compte = {ligne.split("\t")[4]: ligne.split("\t") for ligne in lignes}

    ligne_512 = par_compte["512"]
    assert ligne_512[3] == "20260903"  # EcritureDate, YYYYMMDD
    assert ligne_512[11] == "848.00"  # Debit
    assert ligne_512[12] == "0.00"  # Credit

    ligne_706 = par_compte["706"]
    assert ligne_706[11] == "0.00"
    assert ligne_706[12] == "945.45"


def test_libelle_compte_et_journal_renseignes() -> None:
    fec = exporter_fec((_ecriture_uber(),))
    ligne_512 = next(ligne for ligne in fec.split("\n") if "\t512\t" in ligne)
    champs = ligne_512.split("\t")
    assert champs[0] == "BQ"
    assert champs[1] == "Banque"
    assert champs[5] == "Banques"  # CompteLib


def test_trie_par_date() -> None:
    plus_recente = Ecriture(
        id=EcritureId("e2"),
        dossier_id=DOSSIER,
        journal=Journal.OD,
        date=date(2026, 9, 10),
        libelle="Plus tard",
        reference_piece=None,
        lignes=(
            LigneEcriture("512", Sens.DEBIT, Money(10_00)),
            LigneEcriture("706", Sens.CREDIT, Money(10_00)),
        ),
    )
    fec = exporter_fec((plus_recente, _ecriture_uber()))
    dates = [ligne.split("\t")[3] for ligne in fec.strip("\n").split("\n")[1:]]
    assert dates == sorted(dates)
