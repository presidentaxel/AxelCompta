"""Écritures d'inventaire générées à la clôture (doc 06 §5), datées du
dernier jour de l'exercice, journal OD :

1. **Liquidation de la TVA** : solde les comptes 4457x (collectée) et 4456x
   (déductible) sur 44551 (TVA à décaisser) ou 44567 (crédit de TVA).
2. **Impôt sur les sociétés** : 695 au débit, 444 au crédit.

Elles ne sont jamais écrites dans le ledger : recalculées à chaque clôture
depuis le grand livre, comme la liasse elle-même, puis ajoutées aux exports
(FEC, grand livre, balance) pour que tous les documents concordent.
"""

from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

COMPTE_TVA_A_DECAISSER = "44551"
COMPTE_CREDIT_TVA = "44567"
COMPTE_IS_CHARGE = "695"
COMPTE_IS_DETTE = "444"


def _ligne(compte: str, sens: Sens, centimes: int) -> LigneEcriture:
    return LigneEcriture(compte=compte, sens=sens, montant=Money(centimes))


def _contrepassation(compte: str, solde: int) -> LigneEcriture:
    """Ligne qui ramène `compte` à zéro (solde débiteur → crédit)."""
    return _ligne(compte, Sens.CREDIT if solde > 0 else Sens.DEBIT, abs(solde))


def id_cloture_tva(dossier_id: DossierId, annee: int) -> EcritureId:
    return EcritureId(f"{dossier_id}:cloture-tva-{annee}")


def id_cloture_is(dossier_id: DossierId, annee: int) -> EcritureId:
    return EcritureId(f"{dossier_id}:cloture-is-{annee}")


def ecriture_liquidation_tva(
    dossier_id: DossierId, balance: dict[str, int], date_cloture: date
) -> Ecriture | None:
    comptes_tva = sorted(
        c for c, s in balance.items() if s and (c.startswith("4456") or c.startswith("4457"))
    )
    if not comptes_tva:
        return None
    lignes = [_contrepassation(c, balance[c]) for c in comptes_tva]
    # Somme des soldes 4456 (débiteurs) + 4457 (créditeurs, négatifs) :
    # négative = TVA due, positive = crédit à reporter.
    net = sum(balance[c] for c in comptes_tva)
    if net < 0:
        lignes.append(_ligne(COMPTE_TVA_A_DECAISSER, Sens.CREDIT, -net))
    elif net > 0:
        lignes.append(_ligne(COMPTE_CREDIT_TVA, Sens.DEBIT, net))
    return Ecriture(
        id=id_cloture_tva(dossier_id, date_cloture.year),
        dossier_id=dossier_id,
        journal=Journal.OD,
        date=date_cloture,
        libelle="Liquidation de la TVA de l'exercice",
        reference_piece=f"CLOTURE-TVA-{date_cloture.year}",
        lignes=tuple(lignes),
    )


def ecriture_impot_societes(
    dossier_id: DossierId, impot_euros: int, date_cloture: date
) -> Ecriture | None:
    if impot_euros <= 0:
        return None
    centimes = impot_euros * 100
    return Ecriture(
        id=id_cloture_is(dossier_id, date_cloture.year),
        dossier_id=dossier_id,
        journal=Journal.OD,
        date=date_cloture,
        libelle="Impôt sur les sociétés de l'exercice",
        reference_piece=f"CLOTURE-IS-{date_cloture.year}",
        lignes=(
            _ligne(COMPTE_IS_CHARGE, Sens.DEBIT, centimes),
            _ligne(COMPTE_IS_DETTE, Sens.CREDIT, centimes),
        ),
    )
