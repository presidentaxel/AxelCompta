"""Exports comptables — grand livre et balance en CSV (doc 06 §6 : « pour
l'expert-comptable du client »). Le journal, c'est le FEC (`fec.py`) — le
format légal, pas la peine d'en avoir un deuxième pour la même donnée.

Servent à **tracer une erreur** (2026-09-05, suite à « s'il est faux, on ne
sait pas ») : le grand livre montre chaque mouvement d'un compte donné, la
balance montre le solde de chaque compte — de quoi remonter du chiffre de
la liasse jusqu'à l'écriture précise qui l'a produit.
"""

from __future__ import annotations

import csv
import io

from axelcompta.ledger.models import Ecriture, Sens

from .fec import libelle_compte


def exporter_grand_livre(ecritures: tuple[Ecriture, ...]) -> str:
    """Une ligne par ligne d'écriture, triée par compte puis par date — la
    présentation attendue d'un grand livre, à l'inverse du FEC (trié par
    date, l'ordre chronologique légal)."""
    paires = sorted(
        ((ecriture, ligne) for ecriture in ecritures for ligne in ecriture.lignes),
        key=lambda paire: (paire[1].compte, paire[0].date),
    )
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon)
    ecrivain.writerow(
        ["compte", "libelle_compte", "date", "ecriture_id", "libelle_ecriture", "sens", "montant"]
    )
    for ecriture, ligne in paires:
        ecrivain.writerow(
            [
                ligne.compte,
                libelle_compte(ligne.compte),
                ecriture.date.isoformat(),
                ecriture.id,
                ecriture.libelle,
                ligne.sens.name,
                f"{ligne.montant.centimes / 100:.2f}",
            ]
        )
    return tampon.getvalue()


def exporter_balance(ecritures: tuple[Ecriture, ...]) -> str:
    """compte, libellé, total débit, total crédit, solde (doc 06 §6)."""
    totaux: dict[str, list[int]] = {}  # compte -> [debit_cts, credit_cts]
    for ecriture in ecritures:
        for ligne in ecriture.lignes:
            debit_credit = totaux.setdefault(ligne.compte, [0, 0])
            index = 0 if ligne.sens is Sens.DEBIT else 1
            debit_credit[index] += ligne.montant.centimes

    tampon = io.StringIO()
    ecrivain = csv.writer(tampon)
    ecrivain.writerow(["compte", "libelle_compte", "debit", "credit", "solde"])
    for compte in sorted(totaux):
        debit_cts, credit_cts = totaux[compte]
        ecrivain.writerow(
            [
                compte,
                libelle_compte(compte),
                f"{debit_cts / 100:.2f}",
                f"{credit_cts / 100:.2f}",
                f"{(debit_cts - credit_cts) / 100:.2f}",
            ]
        )
    return tampon.getvalue()
