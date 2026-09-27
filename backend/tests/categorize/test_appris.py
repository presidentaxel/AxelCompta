from __future__ import annotations

from axelcompta.categorize.appris import (
    OperationTranchee,
    libelle_sans_categorie,
    normaliser,
    propositions_apprises,
)

SALAIRE = OperationTranchee(
    "SOLDE SALAIRE JUIN 2025 SEMAINE 1 CAMILLE MARTIN", -120_000, "salaires_personnel"
)


def test_une_operation_semblable_reprend_la_categorie_tranchee() -> None:
    [proposition] = propositions_apprises(
        [SALAIRE], [("SOLDE SALAIRE JUIN 2025 SEMAINE 3 LEA DUPONT", -95_000)]
    )
    assert proposition is not None
    assert proposition.categorie == "salaires_personnel"


def test_le_sens_contraire_ne_reprend_jamais_la_categorie() -> None:
    """Un salaire reçu n'est pas un salaire versé."""
    assert propositions_apprises(
        [SALAIRE], [("SOLDE SALAIRE JUIN 2025 SEMAINE 1 CAMILLE MARTIN", 120_000)]
    ) == [None]


def test_une_operation_sans_rapport_reste_sans_proposition() -> None:
    assert propositions_apprises([SALAIRE], [("CB TOTAL ACCESS A6", -4_500)]) == [None]


def test_sans_decision_rien_n_est_propose() -> None:
    assert propositions_apprises([], [("CB TOTAL", -4_500), ("UBER", 30_000)]) == [None, None]


def test_le_voisin_le_plus_proche_l_emporte() -> None:
    tranchees = [
        OperationTranchee("PRLV SEPA SFR MOBILE", -2_999, "telecommunications"),
        OperationTranchee("PRLV SEPA AXA ASSURANCE AUTO", -8_000, "assurance_vehicule"),
    ]
    [proposition] = propositions_apprises(tranchees, [("PRLV SEPA AXA ASSURANCE AUTO 09", -8_000)])
    assert proposition is not None
    assert proposition.categorie == "assurance_vehicule"


def test_les_chiffres_et_la_categorie_collee_ne_comptent_pas() -> None:
    assert normaliser("Acompte Salaire 12/06 Réf 4411") == "acompte salaire ref"
    assert libelle_sans_categorie("SOLDE SALAIRE (recettes_plateformes)") == "SOLDE SALAIRE"
