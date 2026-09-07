from __future__ import annotations

import pytest

from axelcompta.demo_comptes import SupabaseConfig


def test_depuis_env_leve_si_url_manquante(monkeypatch: pytest.MonkeyPatch) -> None:
    """doc 08 §2.7 : pas de valeur par défaut silencieuse."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "peu-importe")
    with pytest.raises(RuntimeError):
        SupabaseConfig.depuis_env()


def test_depuis_env_leve_si_service_role_key_manquante(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://exemple.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(RuntimeError):
        SupabaseConfig.depuis_env()


def test_depuis_env_construit_la_config_si_tout_est_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://exemple.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "une-cle")
    config = SupabaseConfig.depuis_env()
    assert config.url == "https://exemple.supabase.co"
    assert config.service_role_key == "une-cle"
