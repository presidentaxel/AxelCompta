"""Tests unitaires du classement de consentement DSP2."""

from __future__ import annotations

from datetime import date, datetime

from axelcompta.ingestion.consentement import (
    SanteConnexion,
    StatutConsentement,
    classer,
    expiration_la_plus_proche,
    relever_sante,
)

AUJOURDHUI = date(2026, 9, 24)


def test_sans_date_cest_jamais_connecte() -> None:
    assert classer(None, AUJOURDHUI) is StatutConsentement.JAMAIS_CONNECTE


def test_date_passee_est_expiree() -> None:
    assert classer(date(2026, 9, 23), AUJOURDHUI) is StatutConsentement.EXPIRE


def test_dans_quatorze_jours_est_a_renouveler() -> None:
    assert classer(date(2026, 10, 8), AUJOURDHUI) is StatutConsentement.A_RENOUVELER


def test_au_dela_de_quatorze_jours_reste_actif() -> None:
    assert classer(date(2026, 10, 9), AUJOURDHUI) is StatutConsentement.ACTIF


def test_liste_vide_na_pas_de_date() -> None:
    assert expiration_la_plus_proche([]) is None


def test_retient_la_date_la_plus_tot_et_ignore_la_sentinelle() -> None:
    payload = [
        {"item": {"authentication_expires_at": "0000-00-00 00:00:00"}},
        {"item": {"authentication_expires_at": "2026-12-01 10:00:00"}},
        {"item": {"authentication_expires_at": "2026-10-02 08:00:00"}},
    ]
    assert expiration_la_plus_proche(payload) == date(2026, 10, 2)


def test_sans_compte_la_connexion_nest_pas_etablie() -> None:
    assert relever_sante([]).statut is SanteConnexion.JAMAIS_CONNECTE


def test_sca_requise_prime_sur_la_pause() -> None:
    payload = {
        "a": {"paused": True, "data_access": True, "item": {"status_code_info": "ok"}},
        "b": {
            "paused": False,
            "data_access": True,
            "item": {"status_code_info": "sca_required_webview"},
        },
    }
    assert relever_sante(payload).statut is SanteConnexion.AUTH_REQUISE


def test_sans_acces_puis_pause_puis_ok() -> None:
    assert relever_sante([{"data_access": False, "item": {"status_code_info": "ok"}}]).statut is (
        SanteConnexion.SANS_ACCES
    )
    assert relever_sante([{"paused": True, "data_access": True, "item": {}}]).statut is (
        SanteConnexion.EN_PAUSE
    )
    ok = [{"paused": False, "data_access": True, "item": {"status_code_info": "ok"}}]
    assert relever_sante(ok).statut is SanteConnexion.OK


def test_retient_le_rafraichissement_le_plus_ancien_et_ignore_la_sentinelle() -> None:
    payload = [
        {"item": {"last_successful_refresh": "0000-00-00 00:00:00", "status_code_info": "ok"}},
        {"data_access": True, "item": {"last_successful_refresh": "2026-09-20 08:00:00"}},
        {"data_access": True, "item": {"last_successful_refresh": "2026-09-01 08:00:00"}},
    ]
    releve = relever_sante(payload)
    assert releve.dernier_rafraichissement == datetime(2026, 9, 1, 8, 0, 0)
