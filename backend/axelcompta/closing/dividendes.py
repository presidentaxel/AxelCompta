"""Versement des dividendes décidés à l'affectation (compte 457).

Pour un associé personne physique, la société retient à la source et
reverse elle-même, avec la déclaration 2777, au plus tard le 15 du mois qui
suit le paiement :
- le prélèvement forfaitaire non libératoire de 12,8 % (CGI art. 117
  quater), sauf si l'associé en a demandé la dispense (revenu fiscal de
  référence sous le seuil légal, demande faite avant le 30 novembre de
  l'année précédente) ;
- les prélèvements sociaux, toujours (CSG, CRDS, prélèvement de
  solidarité).

L'écriture passe les retenues : 457 au débit, 4423 au crédit. Le reste suit
la banque, catégorisé par le chauffeur : son virement net solde le 457
(« Mes dividendes »), le paiement de la 2777 solde le 4423 (« Impôts sur
mes dividendes »).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

from .affectation import fiscalite

COMPTE_DIVIDENDES, COMPTE_RETENUES = "457", "4423"


@dataclass(frozen=True, slots=True)
class RetenuesDividendes:
    """En centimes : ce que la société retient et déclare en 2777."""

    brut: int
    prelevement_forfaitaire: int
    csg: int
    crds: int
    solidarite: int
    verse_le: date
    dispense_prelevement: bool

    @property
    def total_retenu(self) -> int:
        return self.prelevement_forfaitaire + self.csg + self.crds + self.solidarite

    @property
    def net_a_virer(self) -> int:
        return self.brut - self.total_retenu

    @property
    def echeance_2777(self) -> date:
        """Le 15 du mois qui suit le paiement."""
        if self.verse_le.month == 12:
            return date(self.verse_le.year + 1, 1, 15)
        return date(self.verse_le.year, self.verse_le.month + 1, 15)


def _part(montant: int, taux: Decimal) -> int:
    return int((montant * taux).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def retenues(brut: int, verse_le: date, dispense_prelevement: bool) -> RetenuesDividendes:
    """Taux de l'année du versement (`fiscalite_dividendes.toml`)."""
    taux = fiscalite(verse_le.year)
    return RetenuesDividendes(
        brut=brut,
        prelevement_forfaitaire=0 if dispense_prelevement else _part(brut, taux.pfu_impot_revenu),
        csg=_part(brut, taux.csg),
        crds=_part(brut, taux.crds),
        solidarite=_part(brut, taux.solidarite),
        verse_le=verse_le,
        dispense_prelevement=dispense_prelevement,
    )


def id_retenues(dossier_id: DossierId, annee_exercice: int) -> EcritureId:
    return EcritureId(f"{dossier_id}:retenues-dividendes-{annee_exercice}")


def ecriture_retenues(
    dossier_id: DossierId, annee_exercice: int, detail: RetenuesDividendes
) -> Ecriture:
    montant = Money(detail.total_retenu)
    return Ecriture(
        id=id_retenues(dossier_id, annee_exercice),
        dossier_id=dossier_id,
        journal=Journal.OD,
        date=detail.verse_le,
        libelle=f"Retenues à la source sur les dividendes {annee_exercice} (2777)",
        reference_piece=f"DIVIDENDES-{annee_exercice}",
        lignes=(
            LigneEcriture(COMPTE_DIVIDENDES, Sens.DEBIT, montant),
            LigneEcriture(COMPTE_RETENUES, Sens.CREDIT, montant),
        ),
    )
