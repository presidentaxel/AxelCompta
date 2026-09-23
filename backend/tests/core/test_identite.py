from __future__ import annotations

from axelcompta.core.identite import Adresse
from axelcompta.demo_identites import IDENTITE_KARIM


def test_siret_est_siren_plus_nic() -> None:
    assert IDENTITE_KARIM.siret == "98714203100010"


def test_dirigeant_est_le_premier_associe() -> None:
    assert IDENTITE_KARIM.dirigeant.nom == "AMRANI"


def test_adresse_sur_une_ligne() -> None:
    adresse = Adresse("6", "avenue Jean Jaurès", "92120", "Montrouge")
    assert adresse.sur_une_ligne() == "6 avenue Jean Jaurès, 92120 Montrouge"
