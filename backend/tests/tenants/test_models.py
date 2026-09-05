from __future__ import annotations

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.tenants.models import Dossier, Tenant


def test_dossier_porte_sa_config_complete() -> None:
    dossier = Dossier(
        id=DossierId("d1"),
        tenant_id=TenantId("t1"),
        forme_juridique="SASU",
        regime_imposition="IS",
        regime_tva="reel_normal",
    )
    assert dossier.forme_juridique == "SASU"
    assert dossier.regime_tva == "reel_normal"


def test_tenant_ne_porte_que_son_id() -> None:
    assert Tenant(id=TenantId("t1")).id == "t1"
