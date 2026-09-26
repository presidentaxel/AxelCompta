"""Seuils de la franchise en base de TVA, prestations de services
(BOI-TVA-DECLA-40-10-10-20260701, § 130, § 140, § 285)."""

from __future__ import annotations

from datetime import date

import pytest

from axelcompta.tenants.franchise_tva import (
    EtatFranchise,
    MillesimeInconnu,
    seuils,
    suivre_franchise,
)


@pytest.mark.parametrize(
    ("ca_eur", "etat"),
    [
        (20_000, EtatFranchise.SOUS_LE_SEUIL),
        (33_750, EtatFranchise.APPROCHE),  # 90 % du seuil de base
        (37_500, EtatFranchise.APPROCHE),  # atteindre n'est pas dépasser
        (37_501, EtatFranchise.SEUIL_BASE_DEPASSE),
        (41_250, EtatFranchise.SEUIL_BASE_DEPASSE),
        (41_251, EtatFranchise.SEUIL_MAJORE_DEPASSE),
    ],
)
def test_etat_selon_le_chiffre_d_affaires(ca_eur: int, etat: EtatFranchise) -> None:
    assert suivre_franchise(ca_eur * 100, 2026).etat is etat


def test_messages_disent_quand_la_tva_devient_due() -> None:
    base = suivre_franchise(38_000_00, 2026).message
    majore = suivre_franchise(42_000_00, 2026).message
    assert base is not None and "1er janvier 2027" in base
    assert majore is not None and "depuis la date du dépassement" in majore
    assert suivre_franchise(10_000_00, 2026).message is None


def test_seuils_au_prorata_la_premiere_annee() -> None:
    # Début le 1er juillet 2026 : 184 jours restants sur 365.
    limites = seuils(2026, debut_activite=date(2026, 7, 1))
    assert limites.base_cts == 37_500_00 * 184 // 365
    assert limites.majore_cts == 41_250_00 * 184 // 365
    assert seuils(2026, debut_activite=date(2024, 3, 1)).base_cts == 37_500_00


def test_une_annee_sans_seuils_connus_n_emprunte_pas_ceux_d_une_autre() -> None:
    with pytest.raises(MillesimeInconnu):
        suivre_franchise(10_000_00, 2031)
