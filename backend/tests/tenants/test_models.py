from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.tenants.models import Dossier, Tenant


def test_dossier_porte_sa_config_complete() -> None:
    dossier = Dossier(
        id=DossierId("d1"),
        tenant_id=TenantId("t1"),
        forme_juridique="SASU",
        regime_imposition="IS",
        regime_tva="reel_normal",
        nom="Dossier test",
        tva_recettes_regime="assujetti_taux_reduit",
        exercice_debut=date(2025, 1, 1),
    )
    assert dossier.forme_juridique == "SASU"
    assert dossier.regime_tva == "reel_normal"


def test_tenant_ne_porte_que_son_id() -> None:
    assert Tenant(id=TenantId("t1")).id == "t1"
