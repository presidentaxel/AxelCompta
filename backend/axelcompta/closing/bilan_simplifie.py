"""Clôture simplifiée (doc 17 §3, semaine 3) : balance → compte de résultat
→ bilan → LiassePivot. Réduit au strict nécessaire pour le récit de démo —
pas de rapprochement bancaire, pas de dotations aux amortissements, pas de
cadrage TVA de clôture, pas de réintégrations fiscales (doc 06 §5, la
checklist complète, V1 seulement).

**Limite trouvée en testant sur un vrai dossier complet** (doc 17 §2,
reformulé 2026-09-05) : `TRESORERIE == RESULTAT + TVA_A_PAYER` ne tient que
si *toutes* les transactions du grand livre touchent un compte classe 6/7
(charge/produit). Dès qu'une transaction touche un compte hors compte de
résultat (immobilisation, capital — `nature_depuis_compte` renvoie
`"autre"`), la trésorerie s'écarte du résultat d'exactement ce montant,
puisqu'on ne modélise pas de poste de bilan séparé pour ces comptes (pas de
ligne « immobilisations », pas de ligne « capital »). Assumé pour la démo,
pas un bug — voir tests/test_demo_dossier_reel.py pour un cas concret.
"""

from __future__ import annotations

from axelcompta.core.ids import DossierId
from axelcompta.core.pcg import nature_depuis_compte
from axelcompta.ledger.models import Ecriture, Sens
from axelcompta.ledger.service import LedgerService

from .models import LiassePivot
from .service import ClosingService


def _solde_par_compte(ecritures: tuple[Ecriture, ...]) -> dict[str, int]:
    balance: dict[str, int] = {}
    for ecriture in ecritures:
        for ligne in ecriture.lignes:
            signe = 1 if ligne.sens is Sens.DEBIT else -1
            balance[ligne.compte] = balance.get(ligne.compte, 0) + signe * ligne.montant.centimes
    return balance


def _compte_de_resultat(balance: dict[str, int]) -> tuple[int, int]:
    """(produits, charges) en centimes, toujours positifs — un solde de
    compte produit (classe 7) est créditeur donc négatif dans `balance`."""
    produits = sum(
        -solde for compte, solde in balance.items() if nature_depuis_compte(compte) == "produit"
    )
    charges = sum(
        solde for compte, solde in balance.items() if nature_depuis_compte(compte) == "charge"
    )
    return produits, charges


class ClotureSimplifieeService(ClosingService):
    """doc 17 §3, semaine 3 : compte de résultat + bilan simplifiés, une
    seule case fiscale (2065 = résultat comptable, aucune réintégration —
    hors scope démo)."""

    def __init__(self, ledger: LedgerService) -> None:
        self._ledger = ledger

    def cloturer(self, dossier_id: DossierId, exercice: str) -> LiassePivot:
        ecritures = self._ledger.grand_livre(dossier_id)
        balance = _solde_par_compte(ecritures)
        produits, charges = _compte_de_resultat(balance)
        resultat = produits - charges
        # TVA nette due = collectée (44571, crédit) - déductible (44566, débit)
        tva_a_payer = -balance.get("44571", 0) - balance.get("44566", 0)
        dates = [ecriture.date for ecriture in ecritures]
        return LiassePivot(
            dossier_id=dossier_id,
            exercice=exercice,
            cases={
                "CA_HT": produits,
                "CHARGES": charges,
                "RESULTAT": resultat,
                "TRESORERIE": balance.get("512", 0),
                "TVA_A_PAYER": tva_a_payer,
                "2065": resultat,  # case-clé du formulaire 2065 (doc 17 §3)
            },
            # Bornes réelles de l'exercice (doc 06 §7 : un exercice peut être
            # partiel, création en cours d'année) — pas une hypothèse année
            # civile qui serait fausse pour un dossier réel créé en cours
            # d'exercice.
            exercice_debut=min(dates) if dates else None,
            exercice_fin=max(dates) if dates else None,
        )
