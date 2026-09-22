from __future__ import annotations

from datetime import date

import pytest

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.tenants.memory import InMemoryDossierRepository
from axelcompta.tenants.models import Dossier, Tenant


def _dossier(dossier_id: str, tenant_id: str, contact_nr: str | None = None) -> Dossier:
    return Dossier(
        id=DossierId(dossier_id),
        tenant_id=TenantId(tenant_id),
        forme_juridique="SASU",
        regime_imposition="IS",
        regime_tva="reel_normal",
        nom="Test",
        tva_recettes_regime="franchise",
        exercice_debut=date(2025, 1, 1),
        contact_nr=contact_nr,
    )


def test_un_dossier_dun_tenant_inconnu_est_refuse() -> None:
    with pytest.raises(ValueError):
        InMemoryDossierRepository().enregistrer(_dossier("d1", "fantome"))


def test_lister_par_tenant_ne_renvoie_que_ce_portefeuille() -> None:
    repo = InMemoryDossierRepository()
    for t in ("a", "b"):
        repo.enregistrer_tenant(Tenant(id=TenantId(t), nom=t))
    repo.enregistrer(_dossier("d2", "a"))
    repo.enregistrer(_dossier("d1", "a"))
    repo.enregistrer(_dossier("d3", "b"))

    assert [d.id for d in repo.lister_par_tenant(TenantId("a"))] == ["d1", "d2"]


def test_correspondance_contact_digifactory() -> None:
    repo = InMemoryDossierRepository()
    repo.enregistrer_tenant(Tenant(id=TenantId("t"), nom="t"))
    repo.enregistrer(_dossier("d1", "t", contact_nr="42"))

    assert repo.par_contact_nr("42") is not None
    assert repo.par_contact_nr("43") is None
