"""Invariants purs du moteur comptable (doc 06 §1) — aucune I/O ici, c'est ce
qui rend ce module testable sans base de données (doc 08 §2.1).
"""

from __future__ import annotations

from axelcompta.core.errors import InvariantViole
from axelcompta.core.money import Money

from .models import Ecriture, Sens


def solde(ecriture: Ecriture) -> tuple[Money, Money]:
    """(total débit, total crédit) — jamais None, jamais partiel."""
    debits = tuple(ligne.montant for ligne in ecriture.lignes if ligne.sens is Sens.DEBIT)
    credits = tuple(ligne.montant for ligne in ecriture.lignes if ligne.sens is Sens.CREDIT)
    return Money.somme(debits), Money.somme(credits)


def verifier_equilibre(ecriture: Ecriture) -> None:
    """Lève InvariantViole si débit ≠ crédit — jamais persisté déséquilibré
    (doc 06 §1). Une écriture sans ligne est aussi refusée : 0 = 0 n'est pas
    une écriture valide.
    """
    if not ecriture.lignes:
        raise InvariantViole(f"écriture {ecriture.id} n'a aucune ligne")
    debit, credit = solde(ecriture)
    if debit != credit:
        raise InvariantViole(
            f"écriture {ecriture.id} déséquilibrée : débit={debit.centimes} "
            f"crédit={credit.centimes} centimes"
        )
