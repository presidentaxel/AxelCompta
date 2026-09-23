from __future__ import annotations

from datetime import date

from axelcompta.closing.ecritures_cloture import ecriture_impot_societes, ecriture_liquidation_tva
from axelcompta.core.ids import DossierId
from axelcompta.ledger.models import Ecriture, Journal, Sens

DOSSIER = DossierId("d1")
CLOTURE = date(2025, 12, 31)


def _soldes(ecriture: Ecriture) -> dict[str, int]:
    soldes: dict[str, int] = {}
    for ligne in ecriture.lignes:
        signe = 1 if ligne.sens is Sens.DEBIT else -1
        soldes[ligne.compte] = soldes.get(ligne.compte, 0) + signe * ligne.montant.centimes
    return soldes


def test_liquidation_tva_a_decaisser_equilibree() -> None:
    ecriture = ecriture_liquidation_tva(DOSSIER, {"44571": -1_372_49, "44566": 464_44}, CLOTURE)
    assert ecriture is not None
    assert ecriture.journal is Journal.OD and ecriture.date == CLOTURE
    soldes = _soldes(ecriture)
    assert soldes == {"44571": 1_372_49, "44566": -464_44, "44551": -908_05}
    assert sum(soldes.values()) == 0


def test_credit_de_tva_quand_la_deductible_depasse() -> None:
    ecriture = ecriture_liquidation_tva(DOSSIER, {"44571": -100_00, "44566": 300_00}, CLOTURE)
    assert ecriture is not None
    assert _soldes(ecriture)["44567"] == 200_00


def test_pas_de_tva_pas_d_ecriture() -> None:
    assert ecriture_liquidation_tva(DOSSIER, {"512": 10_00, "706": -10_00}, CLOTURE) is None


def test_impot_societes_695_444() -> None:
    ecriture = ecriture_impot_societes(DOSSIER, 185, CLOTURE)
    assert ecriture is not None
    assert _soldes(ecriture) == {"695": 185_00, "444": -185_00}
    assert ecriture_impot_societes(DOSSIER, 0, CLOTURE) is None
