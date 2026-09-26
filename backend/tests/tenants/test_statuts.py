"""Matrice statut × régime (doc 06 §7) et validation de la configuration
d'un dossier."""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from axelcompta.core.ids import DossierId, TenantId
from axelcompta.tenants.memory import InMemoryDossierRepository
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.tenants.statuts import (
    ConfigurationInvalide,
    FormeJuridique,
    RegimeImposition,
    charger_matrice,
    configuration_de,
    erreurs_configuration,
)

BASE = Dossier(
    id=DossierId("d1"),
    tenant_id=TenantId("t"),
    forme_juridique="SASU",
    regime_imposition="IS",
    regime_tva="reel_normal",
    nom="d1",
    tva_recettes_regime="assujetti_taux_reduit",
    exercice_debut=date(2026, 1, 1),
)


def _avec(**champs: object) -> Dossier:
    return dataclasses.replace(BASE, **champs)  # type: ignore[arg-type]


def test_la_matrice_versionnee_se_charge_et_chaque_combinaison_a_sa_colonne() -> None:
    matrice = charger_matrice()
    assert matrice.version
    assert set(matrice.combinaisons.values()) == set(matrice.colonnes)
    seule_operationnelle = [c.cle for c in matrice.colonnes.values() if c.disponible]
    assert seule_operationnelle == ["societe_is"]


@pytest.mark.parametrize(
    ("forme", "regime", "colonne"),
    [
        ("SASU", "IS", "societe_is"),
        ("SAS", "IS", "societe_is"),
        ("EURL", "IS", "societe_is"),
        ("SARL", "IS", "societe_is"),
        ("SASU", "option_IR", "societe_ir"),
        ("EURL", "IR", "societe_ir"),
        ("EI", "IR", "ei_reel"),
        ("EI", "micro", "micro"),
    ],
)
def test_chaque_statut_du_pilote_trouve_sa_colonne(forme: str, regime: str, colonne: str) -> None:
    option = 2025 if regime == "option_IR" else None
    dossier = _avec(forme_juridique=forme, regime_imposition=regime, option_ir_debut=option)

    configuration = configuration_de(dossier)

    assert configuration.forme is FormeJuridique(forme)
    assert configuration.regime_imposition is RegimeImposition(regime)
    assert configuration.colonne.cle == colonne


def test_la_colonne_porte_ce_que_le_moteur_lit() -> None:
    is_ = configuration_de(BASE).colonne
    ei = configuration_de(_avec(forme_juridique="EI", regime_imposition="IR")).colonne
    micro = configuration_de(_avec(forme_juridique="EI", regime_imposition="micro")).colonne

    assert (is_.soumis_is, is_.compte_usage_personnel, is_.depot_comptes_inpi) == (
        True,
        "455",
        True,
    )
    assert (ei.soumis_is, ei.compte_usage_personnel, ei.depot_comptes_inpi) == (False, "108", False)
    assert micro.compte_usage_personnel is None


@pytest.mark.parametrize(
    ("champs", "attendu"),
    [
        ({"forme_juridique": "SCI"}, "forme juridique « SCI » inconnu"),
        ({"regime_imposition": "IR"}, "une SASU ne peut pas être au régime « IR »"),
        ({"forme_juridique": "EI", "regime_imposition": "IS"}, "une EI ne peut pas"),
        ({"regime_imposition": "option_IR"}, "l'option IR exige l'année"),
        ({"regime_imposition": "option_IR", "option_ir_debut": 2027}, "après l'exercice 2026"),
        ({"regime_imposition": "option_IR", "option_ir_debut": 2021}, "l'exercice 2026 est à l'IS"),
        ({"option_ir_debut": 2025}, "n'a de sens qu'au régime option_IR"),
        ({"regime_tva": "franchise"}, "incohérents : la franchise vaut pour les deux"),
        ({"tva_recettes_regime": "franchise"}, "incohérents"),
        (
            {"regime_tva": "reel_simplifie", "exercice_debut": date(2027, 1, 1)},
            "n'existe plus",
        ),
        ({"pack_metier": "btp"}, "pack métier « btp » inconnu"),
    ],
)
def test_une_configuration_sans_sens_est_refusee(champs: dict[str, object], attendu: str) -> None:
    with pytest.raises(ConfigurationInvalide) as erreur:
        configuration_de(_avec(**champs))
    assert any(attendu in e for e in erreur.value.erreurs), erreur.value.erreurs


def test_la_derniere_annee_de_l_option_ir_est_encore_admise() -> None:
    dossier = _avec(regime_imposition="option_IR", option_ir_debut=2022)
    assert configuration_de(dossier).colonne.cle == "societe_ir"


def test_le_reel_simplifie_reste_lisible_avant_2027() -> None:
    assert erreurs_configuration(_avec(regime_tva="reel_simplifie")) == []


def test_toutes_les_erreurs_remontent_ensemble() -> None:
    erreurs = erreurs_configuration(
        _avec(forme_juridique="SCI", regime_tva="franchise", pack_metier="btp")
    )
    assert len(erreurs) == 3


def test_le_depot_refuse_un_dossier_mal_configure_avant_de_l_ecrire() -> None:
    depot = InMemoryDossierRepository()
    depot.enregistrer_tenant(Tenant(id=TenantId("t"), nom="t"))

    with pytest.raises(ConfigurationInvalide):
        depot.enregistrer(_avec(regime_tva="franchise"))
    assert depot.obtenir(DossierId("d1")) is None


def test_une_matrice_incoherente_est_refusee_au_chargement(tmp_path: Path) -> None:
    fichier = tmp_path / "matrice.toml"
    fichier.write_text(
        'version = "x"\n[colonnes]\n'
        '[[combinaisons]]\nforme = "SASU"\nregime = "IS"\ncolonne = "absente"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="matrice incohérente"):
        charger_matrice(fichier)
