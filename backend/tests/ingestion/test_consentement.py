"""Tests unitaires du classement de consentement DSP2."""

from __future__ import annotations

from datetime import date

from axelcompta.ingestion.consentement import (
    StatutConsentement,
    classer,
    expiration_la_plus_proche,
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
