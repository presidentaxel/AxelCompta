"""Écriture d'à-nouveaux (journal AN) à l'ouverture de l'exercice suivant
(doc 06 §2).

Reprend le solde de chaque compte de bilan (classes 1 à 5) à la clôture, au
premier jour de l'exercice suivant. Les comptes de gestion (classes 6 et 7)
ne se reportent pas : leur solde net est le résultat de l'exercice, porté
en 120 (bénéfice) ou 129 (perte) en attendant son affectation, qui est une
décision de l'associé (ou de l'exploitant) et une écriture à part.
"""

from __future__ import annotations

from datetime import date

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

from .cloture_fiscale import soldes

COMPTE_BENEFICE, COMPTE_PERTE = "120", "129"
CLASSES_DE_BILAN = ("1", "2", "3", "4", "5")


def id_a_nouveaux(dossier_id: DossierId, annee: int) -> EcritureId:
    return EcritureId(f"{dossier_id}:a-nouveaux-{annee}")


def ecriture_a_nouveaux(
    dossier_id: DossierId, ecritures_cloturees: tuple[Ecriture, ...], ouverture: date
) -> Ecriture | None:
    """`ecritures_cloturees` : les écritures **de l'exercice clos**, entre
    ses bornes (ses propres à-nouveaux d'ouverture compris), puis ses
    écritures d'inventaire (sinon la TVA et l'IS manqueraient au bilan
    d'ouverture). Jamais le grand livre entier : les produits et charges
    des exercices antérieurs sont déjà dans leurs à-nouveaux et seraient
    comptés deux fois. `None` si rien n'est à reporter."""
    balance = soldes(ecritures_cloturees)  # débit positif, crédit négatif
    lignes: list[LigneEcriture] = []
    for compte, solde in sorted(balance.items()):
        if solde and compte.startswith(CLASSES_DE_BILAN):
            lignes.append(_ligne(compte, solde))
    resultat = -sum(s for c, s in balance.items() if c.startswith(("6", "7")))
    if resultat:
        compte = COMPTE_BENEFICE if resultat > 0 else COMPTE_PERTE
        lignes.append(_ligne(compte, -resultat))
    if not lignes:
        return None
    return Ecriture(
        id=id_a_nouveaux(dossier_id, ouverture.year),
        dossier_id=dossier_id,
        journal=Journal.AN,
        date=ouverture,
        libelle=f"À-nouveaux au {ouverture.strftime('%d/%m/%Y')}",
        reference_piece=f"AN-{ouverture.year}",
        lignes=tuple(lignes),
    )


def _ligne(compte: str, solde: int) -> LigneEcriture:
    sens = Sens.DEBIT if solde > 0 else Sens.CREDIT
    return LigneEcriture(compte=compte, sens=sens, montant=Money(abs(solde)))
