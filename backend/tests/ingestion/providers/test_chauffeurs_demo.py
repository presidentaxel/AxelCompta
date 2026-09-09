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
from axelcompta.ingestion.providers.base import NormalizedTransaction, PlatformSettlement
from axelcompta.ingestion.providers.chauffeurs_demo import (
    PROFIL_KARIM,
    PROFIL_SOPHIE,
    PROFIL_YANIS,
    PROFILS_DEMO,
    ChauffeurTypeProvider,
    ProfilChauffeurType,
)
from axelcompta.ingestion.reconciliation import EtatReconciliation, reconcilier
from axelcompta.ledger.invariants import solde

TENANT_DEMO = TenantId("demo")
FENETRE_JOURS = 400


def _donnees(
    profil: ProfilChauffeurType,
) -> tuple[tuple[NormalizedTransaction, ...], tuple[PlatformSettlement, ...]]:
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
def test_generation_deterministe(profil: ProfilChauffeurType) -> None:
    transactions_1, settlements_1 = _donnees(profil)
    transactions_2, settlements_2 = _donnees(profil)
    assert transactions_1 == transactions_2
    assert settlements_1 == settlements_2


@pytest.mark.parametrize("profil", PROFILS_DEMO, ids=lambda p: p.nom)
def test_volume_coherent_avec_jusqua_200_jours_actifs(profil: ProfilChauffeurType) -> None:
    """Louis (2026-09-06) : « jusqu'à 5/6 courses/jour ... sur 200 jours »."""
    transactions, settlements = _donnees(profil)
    assert len(settlements) >= 25  # ~200 jours actifs / 7 jours ≈ 28-33 semaines
    assert len(transactions) > len(settlements)  # settlements + dépenses courantes


@pytest.mark.parametrize("profil", PROFILS_DEMO, ids=lambda p: p.nom)
def test_reconciliation_conforme_au_retard_configure(profil: ProfilChauffeurType) -> None:
    """Tous les settlements se réconcilient, **sauf** celui visé par
    `retard_reglement` (Karim, doc 13 §4.2/§4.3) — exercer l'état
    `en_attente_banque` est le but, pas un raté de la génération."""
    transactions, settlements = _donnees(profil)
    resultats = reconcilier(transactions, settlements)
    non_reconcilies = [r for r in resultats if r.etat is not EtatReconciliation.RECONCILIE]
    attendu = 1 if profil.retard_reglement is not None else 0
    assert len(non_reconcilies) == attendu
    if non_reconcilies:
        assert non_reconcilies[0].etat is EtatReconciliation.EN_ATTENTE_BANQUE


@pytest.mark.parametrize("profil", PROFILS_DEMO, ids=lambda p: p.nom)
def test_chaque_ecriture_de_settlement_reconciliee_est_equilibree(
    profil: ProfilChauffeurType,
) -> None:
    """Le vrai test demandé : les calculs (pas juste la génération) tiennent
    sur les 3 régimes (assujetti Karim/Sophie, franchise Yanis) — sur tout
    settlement effectivement réconcilié (le retard de Karim n'en produit
    justement pas, §ci-dessus)."""
    transactions, settlements = _donnees(profil)
    resultats = reconcilier(transactions, settlements)
    reconcilies = [r for r in resultats if r.etat is EtatReconciliation.RECONCILIE]
    assert reconcilies  # au moins un, sinon le test ne prouve rien
    for numero, resultat in enumerate(reconcilies, start=1):
        # resultat.transaction n'est Optional que dans le type de
        # ResultatReconciliation (rempli seulement si RECONCILIE) — le
        # filtre ci-dessus garantit qu'il est présent ici, mypy ne peut
        # pas le déduire lui-même de ce filtre.
        assert resultat.transaction is not None
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
    premier_resultat = resultats[0]
    assert premier_resultat.transaction is not None
    ecriture = construire_ecriture_settlement(
        premier_resultat.transaction,
        premier_resultat.settlement,
        1,
        tva_recettes_regime="franchise",
    )
    assert not any(ligne.compte in ("44566", "44571") for ligne in ecriture.lignes)


def test_sophie_a_bien_deux_plateformes() -> None:
    assert {p.nom for p in PROFIL_SOPHIE.plateformes} == {"uber", "bolt"}


def test_karim_a_une_seule_plateforme_uber() -> None:
    assert {p.nom for p in PROFIL_KARIM.plateformes} == {"uber"}


def test_sophie_a_plusieurs_depenses_ambigues_pas_une_seule() -> None:
    """doc 17 : « il faut 2/3 chauffeurs un peu différents » — poussé plus
    loin le 2026-09-06, la file de revue doit avoir du volume, pas une
    anecdote unique."""
    assert len(PROFIL_SOPHIE.depenses_ponctuelles) >= 3


def test_yanis_change_de_loueur_loa_en_cours_dannee() -> None:
    """Renouvellement de contrat (doc 06 §3.5) : deux dépenses récurrentes
    qui ne se chevauchent pas, à des montants différents."""
    loyers = [d for d in PROFIL_YANIS.depenses_recurrentes if "LOA" in d.libelle]
    assert len(loyers) == 2
    assert {d.montant_cts for d in loyers} == {(378_00, 378_00), (410_00, 410_00)}
    premier, second = sorted(loyers, key=lambda d: d.debut_relatif)
    assert premier.fin_relatif == second.debut_relatif  # pas de trou ni de chevauchement


def test_transaction_en_retard_de_karim_existe_toujours() -> None:
    """Le virement retardé (doc 13 §6, mode dégradé) n'est pas perdu — il
    doit apparaître dans les transactions, juste hors fenêtre de son
    settlement (test précédent)."""
    transactions, _ = _donnees(PROFIL_KARIM)
    assert any(t.montant_cts > 100_00 and "uber" in t.libelle.lower() for t in transactions)
