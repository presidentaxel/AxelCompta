"""Impôt sur les sociétés dû au titre de l'exercice (CGI art. 219).

Taux réduit de 15 % jusqu'à 42 500 € de bénéfice, taux normal de 25 %
au-delà. Le taux réduit suppose une PME au sens de l'art. 219-I-b (CA
< 10 M€, capital entièrement libéré et détenu à 75 % au moins par des
personnes physiques) : c'est le cas de toute SASU/EURL de chauffeur, seul
profil géré aujourd'hui, donc non paramétré.

Sur un exercice qui ne fait pas douze mois, le plafond de 42 500 € est
ajusté prorata temporis (BOI-IS-LIQ-20-10), au nombre de jours.

Base et impôt en euros entiers : la liasse et le relevé de solde (2572)
se remplissent sans centimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

PLAFOND_TAUX_REDUIT_EUROS = 42_500
TAUX_REDUIT = Decimal("0.15")
TAUX_NORMAL = Decimal("0.25")
JOURS_ANNEE = 365


def arrondir_euros(centimes: int) -> int:
    """Centimes → euros entiers, arrondi commercial (0,50 € → 1 €)."""
    return int((Decimal(centimes) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def plafond_taux_reduit(debut: date, fin: date) -> int:
    jours = (fin - debut).days + 1
    if jours == JOURS_ANNEE:
        return PLAFOND_TAUX_REDUIT_EUROS
    prorata = Decimal(PLAFOND_TAUX_REDUIT_EUROS) * jours / JOURS_ANNEE
    return int(prorata.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True, slots=True)
class CalculIS:
    """Tout en euros entiers. `base_taux_reduit + base_taux_normal` vaut le
    résultat fiscal quand il est positif, 0 sinon."""

    base_taux_reduit: int
    base_taux_normal: int
    impot: int


def calculer_is(resultat_fiscal_euros: int, debut: date, fin: date) -> CalculIS:
    if resultat_fiscal_euros <= 0:
        return CalculIS(base_taux_reduit=0, base_taux_normal=0, impot=0)
    plafond = plafond_taux_reduit(debut, fin)
    reduit = min(resultat_fiscal_euros, plafond)
    normal = resultat_fiscal_euros - reduit
    impot = (reduit * TAUX_REDUIT + normal * TAUX_NORMAL).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return CalculIS(base_taux_reduit=reduit, base_taux_normal=normal, impot=int(impot))
