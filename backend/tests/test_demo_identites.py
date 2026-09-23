from __future__ import annotations

from axelcompta.demo_identites import IDENTITES_DEMO
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO


def _luhn(numero: str) -> bool:
    total = 0
    for rang, chiffre in enumerate(reversed(numero)):
        valeur = int(chiffre) * (2 if rang % 2 else 1)
        total += valeur - 9 if valeur > 9 else valeur
    return total % 10 == 0


def test_une_identite_par_chauffeur_de_demo() -> None:
    assert set(IDENTITES_DEMO) == {p.dossier_id for p in PROFILS_DEMO}


def test_siren_et_siret_passent_la_cle_de_controle() -> None:
    for identite in IDENTITES_DEMO.values():
        assert len(identite.siren) == 9 and _luhn(identite.siren)
        assert len(identite.siret) == 14 and _luhn(identite.siret)


def test_courriels_sur_domaine_reserve() -> None:
    # example.com (RFC 2606) : aucun courriel de démo ne peut atteindre quelqu'un.
    for identite in IDENTITES_DEMO.values():
        assert identite.email.endswith(".example.com")


def test_associe_unique_detient_tout_le_capital() -> None:
    for identite in IDENTITES_DEMO.values():
        assert len(identite.associes) == 1
        assert identite.capital_social_cts > 0
        assert identite.associes[0].nb_titres > 0
