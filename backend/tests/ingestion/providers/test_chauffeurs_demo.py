"""Teste le générateur de données des 3 chauffeurs type (doc 17 §4, doc 19).

Objectif principal (Louis, 2026-09-06 : « on veut voir si ça déconne ») :
que les données générées se réconcilient proprement et produisent des
écritures équilibrées pour le régime TVA de chaque profil — pas seulement
que le générateur ne plante pas.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from axelcompta.core.ids import TenantId
from axelcompta.ingestion.ecritures_settlement import construire_ecriture_settlement
from axelcompta.ingestion.providers.chauffeurs_demo import (
    PROFIL_KARIM,
    PROFIL_SOPHIE,
    PROFIL_YANIS,
    PROFILS_DEMO,
    ChauffeurTypeProvider,
)
from axelcompta.ingestion.reconciliation import EtatReconciliation, reconcilier
from axelcompta.ledger.invariants import solde

TENANT_DEMO = TenantId("demo")
FENETRE_JOURS = 400


def _donnees(profil):
    provider = ChauffeurTypeProvider(profil)
    depuis, jusqua = profil.date_debut, profil.date_debut + timedelta(days=FENETRE_JOURS)
    transactions = asyncio.run(
        provider.fetch_transactions(TENANT_DEMO, profil.dossier_id, depuis, jusqua)
    )
    settlements = asyncio.run(
        provider.fetch_platform_settlements(TENANT_DEMO, profil.dossier_id, depuis, jusqua)
    )
    return tuple(transactions), tuple(settlements)


def test_trois_profils_distincts_avec_dossier_id_uniques() -> None:
    ids = {p.dossier_id for p in PROFILS_DEMO}
    assert len(ids) == len(PROFILS_DEMO) == 3


@pytest.mark.parametrize("profil", PROFILS_DEMO, ids=lambda p: p.nom)
def test_generation_deterministe(profil) -> None:
    transactions_1, settlements_1 = _donnees(profil)
    transactions_2, settlements_2 = _donnees(profil)
    assert transactions_1 == transactions_2
    assert settlements_1 == settlements_2


@pytest.mark.parametrize("profil", PROFILS_DEMO, ids=lambda p: p.nom)
def test_volume_coherent_avec_jusqua_200_jours_actifs(profil) -> None:
    """Louis (2026-09-06) : « jusqu'à 5/6 courses/jour ... sur 200 jours »."""
    transactions, settlements = _donnees(profil)
    assert len(settlements) >= 25  # ~200 jours actifs / 7 jours ≈ 28-33 semaines
    assert len(transactions) > len(settlements)  # settlements + dépenses courantes


@pytest.mark.parametrize("profil", PROFILS_DEMO, ids=lambda p: p.nom)
def test_tous_les_settlements_se_reconcilient(profil) -> None:
    """Les montants/dates/libellés générés doivent matcher l'algorithme réel
    (doc 13 §4.2) — pas un mode dégradé propre au test."""
    transactions, settlements = _donnees(profil)
    resultats = reconcilier(transactions, settlements)
    etats = {r.etat for r in resultats}
    assert etats == {EtatReconciliation.RECONCILIE}


@pytest.mark.parametrize("profil", PROFILS_DEMO, ids=lambda p: p.nom)
def test_chaque_ecriture_de_settlement_est_equilibree(profil) -> None:
    """Le vrai test demandé : les calculs (pas juste la génération) tiennent
    sur les 3 régimes (assujetti Karim/Sophie, franchise Yanis)."""
    transactions, settlements = _donnees(profil)
    resultats = reconcilier(transactions, settlements)
    for numero, resultat in enumerate(resultats, start=1):
        ecriture = construire_ecriture_settlement(
            resultat.transaction,
            resultat.settlement,
            numero,
            tva_recettes_regime=profil.tva_recettes_regime,
        )
        debit, credit = solde(ecriture)
        assert debit == credit


def test_yanis_est_bien_en_franchise_sans_tva_sur_commission() -> None:
    transactions, settlements = _donnees(PROFIL_YANIS)
    resultats = reconcilier(transactions, settlements)
    ecriture = construire_ecriture_settlement(
        resultats[0].transaction, resultats[0].settlement, 1, tva_recettes_regime="franchise"
    )
    assert not any(ligne.compte in ("44566", "44571") for ligne in ecriture.lignes)


def test_sophie_a_bien_deux_plateformes() -> None:
    assert {p.nom for p in PROFIL_SOPHIE.plateformes} == {"uber", "bolt"}


def test_karim_a_une_seule_plateforme_uber() -> None:
    assert {p.nom for p in PROFIL_KARIM.plateformes} == {"uber"}
