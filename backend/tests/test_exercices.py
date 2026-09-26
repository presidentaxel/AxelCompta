"""Passage à l'exercice suivant sur les dossiers de démo (exercice 2025,
clos le 31/12/2025) : Karim (sans opération en attente), Sophie (3 en
attente), Yanis (franchise de TVA)."""

from __future__ import annotations

import dataclasses
from datetime import date, datetime

import pytest

from axelcompta import demo_seed
from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.cloture_fiscale import soldes
from axelcompta.closing.impot_societes import arrondir_euros
from axelcompta.closing.models import ParametresCloture
from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.exercices import PassageRefuse, executer_passage, preparer_passage
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens
from axelcompta.tenants.avenants import InMemoryAvenantRegimeRepository, programmer_bascules
from axelcompta.tenants.exercices import InMemoryExerciceRepository
from axelcompta.tenants.memory import InMemoryDossierRepository
from axelcompta.tenants.models import Dossier
from axelcompta.workflow.decisions_memory import InMemoryDecisionRepository
from axelcompta.workflow.propositions import InMemoryPropositionRepository

AUJOURD_HUI = date(2026, 9, 26)
MAINTENANT = datetime(2026, 9, 26, 12, 0)
KARIM, SOPHIE, YANIS = DossierId("DEMO_karim"), DossierId("DEMO_sophie"), DossierId("DEMO_yanis")


class Demo:
    def __init__(self) -> None:
        self.dossiers = InMemoryDossierRepository()
        self.ledger = InMemoryLedgerService()
        self.decisions = InMemoryDecisionRepository()
        self.exercices = InMemoryExerciceRepository()
        demo_seed.amorcer_demo(self.dossiers, self.ledger, InMemoryPropositionRepository())

    def dossier(self, dossier_id: DossierId) -> Dossier:
        dossier = self.dossiers.obtenir(dossier_id)
        assert dossier is not None
        return dossier

    def passer(self, dossier: Dossier, avenants=(), aujourd_hui=AUJOURD_HUI):  # type: ignore[no-untyped-def]
        passage = preparer_passage(dossier, self.ledger, self.decisions, avenants, aujourd_hui)
        executer_passage(passage, self.ledger, self.dossiers, self.exercices, MAINTENANT, "test")
        return passage

    def liasse_2025(self, dossier: Dossier):  # type: ignore[no-untyped-def]
        parametres = ParametresCloture(
            exercice_debut=date(2025, 1, 6),
            exercice_fin=date(2025, 12, 31),
            forme_juridique=dossier.forme_juridique,
            identite=dossier.identite,
        )
        return ClotureSimplifieeService(self.ledger).cloturer(dossier.id, "2025", parametres)


def test_karim_clos_2025_et_ouvre_2026_avec_ses_a_nouveaux() -> None:
    demo = Demo()
    liasse_avant = demo.liasse_2025(demo.dossier(KARIM))

    passage = demo.passer(demo.dossier(KARIM))

    assert [e.reference_piece for e in passage.ecritures] == [
        "CLOTURE-TVA-2025",
        "CLOTURE-IS-2025",
        "AN-2026",
    ]
    a_nouveaux = passage.ecritures[-1]
    assert (a_nouveaux.journal, a_nouveaux.date) == (Journal.AN, date(2026, 1, 1))
    # Le résultat de l'exercice attend son affectation en 120 (bénéfice).
    (ligne_120,) = [ligne for ligne in a_nouveaux.lignes if ligne.compte == "120"]
    assert ligne_120.sens is Sens.CREDIT
    assert ligne_120.montant.centimes == liasse_avant.cases["RESULTAT"]
    assert not any(ligne.compte.startswith(("6", "7")) for ligne in a_nouveaux.lignes)

    ouvert = demo.dossier(KARIM)
    assert (ouvert.exercice_debut, ouvert.fin_exercice()) == (date(2026, 1, 1), date(2026, 12, 31))
    (clos,) = demo.exercices.lister(KARIM)
    assert (clos.debut, clos.fin, clos.clos_par) == (date(2025, 1, 6), date(2025, 12, 31), "test")


def test_la_liasse_2025_ne_bouge_pas_une_fois_l_inventaire_passe_en_base() -> None:
    demo = Demo()
    avant = demo.liasse_2025(demo.dossier(KARIM)).cases

    demo.passer(demo.dossier(KARIM))

    assert demo.liasse_2025(demo.dossier(KARIM)).cases == avant


def test_le_bilan_d_ouverture_2026_reprend_celui_de_cloture_2025() -> None:
    demo = Demo()
    demo.passer(demo.dossier(KARIM))

    grand_livre = demo.ledger.grand_livre(KARIM)
    cloture_2025 = soldes(tuple(e for e in grand_livre if e.date <= date(2025, 12, 31)))
    ouverture = soldes(tuple(e for e in grand_livre if e.reference_piece == "AN-2026"))
    for compte in ("512", "101", "44551"):
        assert ouverture.get(compte, 0) == cloture_2025.get(compte, 0)


def test_rejouer_l_execution_n_ajoute_rien() -> None:
    demo = Demo()
    dossier = demo.dossier(KARIM)
    passage = preparer_passage(dossier, demo.ledger, demo.decisions, (), AUJOURD_HUI)
    executer_passage(passage, demo.ledger, demo.dossiers, demo.exercices, MAINTENANT, "test")
    nb = len(demo.ledger.grand_livre(KARIM))

    executer_passage(passage, demo.ledger, demo.dossiers, demo.exercices, MAINTENANT, "test")

    assert len(demo.ledger.grand_livre(KARIM)) == nb
    assert len(demo.exercices.lister(KARIM)) == 1


def test_refuse_tant_que_des_operations_attendent_une_decision() -> None:
    demo = Demo()
    with pytest.raises(PassageRefuse, match="3 opération"):
        demo.passer(demo.dossier(SOPHIE))
    assert demo.dossier(SOPHIE).exercice_debut == date(2025, 1, 6)


def test_refuse_un_exercice_pas_encore_termine() -> None:
    demo = Demo()
    with pytest.raises(PassageRefuse, match="pas terminé"):
        demo.passer(demo.dossier(KARIM), aujourd_hui=date(2025, 12, 31))


def test_la_fin_d_option_ir_s_applique_au_nouvel_exercice() -> None:
    demo = Demo()
    en_option = dataclasses.replace(
        demo.dossier(KARIM), regime_imposition="option_IR", option_ir_debut=2021
    )
    demo.dossiers.ouvrir_exercice(en_option)
    avenants = InMemoryAvenantRegimeRepository()
    programmer_bascules((en_option,), avenants, MAINTENANT)

    passage = demo.passer(en_option, avenants=avenants.lister(KARIM))

    # À l'IR, pas d'écriture d'IS pour 2025.
    assert [e.reference_piece for e in passage.ecritures] == ["CLOTURE-TVA-2025", "AN-2026"]
    ouvert = demo.dossier(KARIM)
    assert (ouvert.regime_imposition, ouvert.option_ir_debut) == ("IS", None)
    assert passage.changements == ("régime d'imposition : option_IR → IS",)


def test_la_franchise_de_tva_se_perd_au_dela_du_seuil_de_base() -> None:
    demo = Demo()
    montant = Money(30_000_00)  # 12 191 € + 30 000 € > 37 500 €
    demo.ledger.enregistrer(
        Ecriture(
            id=EcritureId("yanis-recettes"),
            dossier_id=YANIS,
            journal=Journal.BQ,
            date=date(2025, 11, 30),
            libelle="Recettes",
            reference_piece=None,
            lignes=(
                LigneEcriture("512", Sens.DEBIT, montant),
                LigneEcriture("706", Sens.CREDIT, montant),
            ),
        )
    )

    passage = demo.passer(demo.dossier(YANIS))

    ouvert = demo.dossier(YANIS)
    assert ouvert.regime_tva == "reel_normal"
    assert ouvert.tva_recettes_regime == "assujetti_taux_reduit"
    assert "sortie de la franchise" in passage.changements[0]


def test_sous_le_seuil_la_franchise_continue() -> None:
    demo = Demo()
    passage = demo.passer(demo.dossier(YANIS))
    assert demo.dossier(YANIS).regime_tva == "franchise"
    assert passage.changements == ()


def test_le_bilan_2026_s_equilibre_avec_le_resultat_2025_en_report_a_nouveau() -> None:
    demo = Demo()
    # Résultat exact au centime : la 2033-B, elle, somme des rubriques
    # arrondies à l'euro et peut s'en écarter d'un euro.
    resultat_2025 = demo.liasse_2025(demo.dossier(KARIM)).cases["RESULTAT"]
    demo.passer(demo.dossier(KARIM))
    ouvert = demo.dossier(KARIM)
    parametres = ParametresCloture(
        exercice_debut=ouvert.exercice_debut,
        exercice_fin=ouvert.fin_exercice(),
        forme_juridique=ouvert.forme_juridique,
        identite=ouvert.identite,
    )

    liasse_2026 = ClotureSimplifieeService(demo.ledger).cloturer(KARIM, "2026", parametres)

    # Pas encore affecté : en report à nouveau, arrondi à l'euro.
    assert liasse_2026.cases["2033A.134"] == arrondir_euros(resultat_2025) * 100
    assert liasse_2026.cases["2033A.136"] == 0  # aucune opération en 2026
    net = liasse_2026.cases["2033A.110"] - liasse_2026.cases["2033A.112"]
    assert net == liasse_2026.cases["2033A.180"]
