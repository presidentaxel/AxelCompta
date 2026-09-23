"""Golden tests de la clôture fiscale sur les chauffeurs de démo : les
chiffres attendus ont été recalculés à la main depuis la balance (voir
les commentaires), pas recopiés depuis la sortie du code."""

from __future__ import annotations

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.cloture_fiscale import soldes
from axelcompta.closing.models import LiassePivot
from axelcompta.demo_chauffeurs_type import construire_ledger, parametres_cloture
from axelcompta.demo_identites import IDENTITES_DEMO
from axelcompta.ingestion.providers.chauffeurs_demo import (
    PROFIL_KARIM,
    PROFIL_YANIS,
    ProfilChauffeurType,
)


def _cloturer(profil: ProfilChauffeurType) -> tuple[LiassePivot, ClotureSimplifieeService]:
    ledger, _ = construire_ledger(profil)
    service = ClotureSimplifieeService(ledger)
    liasse = service.cloturer(profil.dossier_id, "2025", parametres_cloture(profil))
    return liasse, service


def _euros(liasse: LiassePivot, cle: str) -> int:
    return liasse.cases.get(cle, 0) // 100


def test_karim_benefice_is_au_taux_reduit() -> None:
    liasse, _ = _cloturer(PROFIL_KARIM)
    # 310 = 14 191 - 12 957 - 68 (amendes) - 185 (IS) = 981
    assert _euros(liasse, "2033B.310") == 981
    # 370 = 981 + 185 (IS réintégré) + 68 (amendes réintégrées) = 1 234
    assert _euros(liasse, "2033B.370") == 1_234
    assert _euros(liasse, "2065.BENEFICE_TAUX_REDUIT") == 1_234
    assert _euros(liasse, "2065.IMPOT") == _euros(liasse, "2033B.306") == 185  # 15 % × 1 234
    assert liasse.cases["2065"] == 1_234_00


def test_yanis_deficit_reportable() -> None:
    liasse, _ = _cloturer(PROFIL_YANIS)
    assert _euros(liasse, "2033B.310") == -1_346
    # Déficit fiscal = 1 346 - 90 (amende réintégrée) = 1 256, reporté en 2033-D.
    assert _euros(liasse, "2065.DEFICIT") == _euros(liasse, "2033D.870") == 1_256
    assert _euros(liasse, "2065.IMPOT") == 0


def test_bilan_equilibre_et_coherent_avec_le_compte_de_resultat() -> None:
    for profil in (PROFIL_KARIM, PROFIL_YANIS):
        liasse, _ = _cloturer(profil)
        actif_net = _euros(liasse, "2033A.110") - _euros(liasse, "2033A.112")
        assert actif_net == _euros(liasse, "2033A.180")
        assert _euros(liasse, "2033A.136") == _euros(liasse, "2033B.310")
        capital = IDENTITES_DEMO[profil.dossier_id].capital_social_cts // 100
        assert _euros(liasse, "2033A.120") == capital


def test_ecritures_de_cloture_soldent_la_tva_et_portent_l_is() -> None:
    liasse, service = _cloturer(PROFIL_KARIM)
    cloture = service.ecritures_de_cloture(
        PROFIL_KARIM.dossier_id, parametres_cloture(PROFIL_KARIM)
    )
    assert [e.reference_piece for e in cloture] == ["CLOTURE-TVA-2025", "CLOTURE-IS-2025"]
    ledger, _ = construire_ledger(PROFIL_KARIM)
    balance = soldes(ledger.grand_livre(PROFIL_KARIM.dossier_id) + cloture)
    assert balance["44571"] == balance["44566"] == 0
    assert -balance["44551"] == liasse.cases["TVA_A_PAYER"]
    assert balance["695"] == 185_00


def test_identite_et_bornes_declarees_dans_le_pivot() -> None:
    liasse, _ = _cloturer(PROFIL_KARIM)
    assert liasse.identite is not None and liasse.identite.siren == "987142031"
    assert liasse.exercice_fin is not None and liasse.exercice_fin.isoformat() == "2025-12-31"
