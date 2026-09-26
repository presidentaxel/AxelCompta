from __future__ import annotations

from datetime import date

import pytest

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens
from axelcompta.tenants.statuts import FormeJuridique, RegimeImposition, charger_matrice
from axelcompta.workflow.revue import CategorieInconnueError, resoudre_ecriture_a_trancher

COMPTES = {"carburant": "6061"}


def _compte_usage_personnel(forme: str, regime: str) -> str | None:
    colonne = charger_matrice().colonne(FormeJuridique(forme), RegimeImposition(regime))
    assert colonne is not None
    return colonne.compte_usage_personnel


SOCIETE = _compte_usage_personnel("EURL", "IS")


def _ecriture_a_trancher(montant_cts: int = 68_00) -> Ecriture:
    return Ecriture(
        id=EcritureId("e1"),
        dossier_id=DossierId("d1"),
        journal=Journal.BQ,
        date=date(2026, 9, 7),
        libelle="CB ZARA FRANCE (usage_personnel_suspect)",
        reference_piece=None,
        lignes=(
            LigneEcriture(compte="512", sens=Sens.CREDIT, montant=Money(montant_cts)),
            LigneEcriture(compte="471", sens=Sens.DEBIT, montant=Money(montant_cts)),
        ),
    )


@pytest.mark.parametrize(
    ("forme", "regime", "compte"),
    [("EURL", "IS", "455"), ("SASU", "IS", "455"), ("EURL", "IR", "455"), ("EI", "IR", "108")],
)
def test_usage_personnel_suit_la_matrice(forme: str, regime: str, compte: str) -> None:
    resolue = resoudre_ecriture_a_trancher(
        _ecriture_a_trancher(), "usage_personnel", _compte_usage_personnel(forme, regime), COMPTES
    )
    assert {ligne.compte for ligne in resolue.lignes} == {"512", compte}


def test_reclassification_vers_une_categorie_normale_du_pack() -> None:
    """Sophie peut aussi être blanchie : la dépense n'était pas personnelle,
    juste mal catégorisée par le pipeline (doc 05 §5)."""
    ecriture = _ecriture_a_trancher()
    resolue = resoudre_ecriture_a_trancher(ecriture, "carburant", SOCIETE, COMPTES)
    assert {ligne.compte for ligne in resolue.lignes} == {"512", "6061"}


def test_montant_et_sens_inchanges_par_la_reclassification() -> None:
    ecriture = _ecriture_a_trancher(68_00)
    resolue = resoudre_ecriture_a_trancher(ecriture, "usage_personnel", SOCIETE, COMPTES)
    ligne_455 = next(ligne for ligne in resolue.lignes if ligne.compte == "455")
    assert ligne_455.sens is Sens.DEBIT
    assert ligne_455.montant.centimes == 68_00


def test_categorie_inconnue_du_pack_leve_plutot_que_deviner() -> None:
    ecriture = _ecriture_a_trancher()
    with pytest.raises(CategorieInconnueError):
        resoudre_ecriture_a_trancher(ecriture, "categorie_qui_nexiste_pas", SOCIETE, COMPTES)


def test_micro_entreprise_usage_personnel_signale_sans_ecriture() -> None:
    compte = _compte_usage_personnel("EI", "micro")
    assert compte is None
    with pytest.raises(CategorieInconnueError):
        resoudre_ecriture_a_trancher(_ecriture_a_trancher(), "usage_personnel", compte, COMPTES)
