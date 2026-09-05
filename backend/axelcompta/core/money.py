"""Money — montants en centimes entiers.

Invariant absolu (doc 06 §1, doc 08 §2.3) : les flottants sont interdits pour
l'argent. Addition minimale ajoutée pour la démo (doc 17 semaine 0, écriture
et clôture bouchon) ; la ventilation au centime près (doc 09 §2.1) reste à
écrire quand les templates réels (semaine 2) arrivent.
"""

from __future__ import annotations

from dataclasses import dataclass

from axelcompta.core.errors import DomaineError


class DevisesIncompatibles(DomaineError):
    """Additionner deux Money de devises différentes est une erreur métier,
    jamais un arrondi silencieux."""


@dataclass(frozen=True, slots=True)
class Money:
    """Un montant en centimes (int), toujours dans une devise donnée."""

    centimes: int
    devise: str = "EUR"

    def __add__(self, autre: Money) -> Money:
        if autre.devise != self.devise:
            raise DevisesIncompatibles(f"{self.devise} + {autre.devise}")
        return Money(centimes=self.centimes + autre.centimes, devise=self.devise)

    @staticmethod
    def zero(devise: str = "EUR") -> Money:
        return Money(centimes=0, devise=devise)

    @staticmethod
    def somme(montants: tuple[Money, ...], devise: str = "EUR") -> Money:
        total = Money.zero(devise)
        for montant in montants:
            total = total + montant
        return total
