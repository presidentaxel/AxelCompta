"""Bulletin de paie du président assimilé salarié, passé tel quel."""

from __future__ import annotations

from datetime import date

import pytest

from axelcompta.closing.paie import Bulletin, BulletinIncoherent, ecriture_bulletin
from axelcompta.core.ids import DossierId
from axelcompta.ledger.invariants import verifier_equilibre

BULLETIN = Bulletin(
    mois="2026-02",
    brut=2_000_00,
    cotisations_salariales=440_00,
    cotisations_patronales=820_00,
    prelevement_a_la_source=60_00,
)


def test_le_bulletin_s_equilibre_et_tombe_en_fin_de_mois() -> None:
    ecriture = ecriture_bulletin(DossierId("d"), BULLETIN)
    verifier_equilibre(ecriture)
    assert ecriture.date == date(2026, 2, 28)
    montants = {
        (ligne.compte, ligne.sens.name): ligne.montant.centimes for ligne in ecriture.lignes
    }
    assert montants == {
        ("641", "DEBIT"): 2_000_00,
        ("645", "DEBIT"): 820_00,
        ("431", "CREDIT"): 1_260_00,  # 440 + 820
        ("4421", "CREDIT"): 60_00,
        ("421", "CREDIT"): 1_500_00,  # 2 000 - 440 - 60
    }


@pytest.mark.parametrize(
    "champs",
    [
        {"brut": 0},
        {"cotisations_salariales": 2_000_00},
        {"prelevement_a_la_source": -1},
        {"mois": "2026-13"},
    ],
)
def test_un_bulletin_incoherent_est_refuse(champs: dict[str, object]) -> None:
    import dataclasses

    with pytest.raises(BulletinIncoherent):
        ecriture_bulletin(DossierId("d"), dataclasses.replace(BULLETIN, **champs))  # type: ignore[arg-type]
