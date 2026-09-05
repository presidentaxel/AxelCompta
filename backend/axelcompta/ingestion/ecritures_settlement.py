"""Génération d'écritures depuis un settlement réconcilié (doc 13 §5).

Templates de données par régime de commission (doc 13 §5.2) — pas une
branche de code : ajouter une plateforme = ajouter une entrée dans
`TEMPLATES_COMMISSION`, pas un `if`. Le taux de TVA sur les recettes
(doc 13 §5.1, configurable par dossier) est ici figé à 10 % assujetti — le
profil unique de la démo (doc 17 §3 : « assujetti 10% sur recettes, pas de
franchise »).

Ne dépend pas de `ledger` pour ses règles de calcul : celles-ci sont pures
(`_ventiler`). Dépend de `ledger.models` uniquement pour construire l'objet
`Ecriture` — `ledger` lui-même ne dépend jamais d'`ingestion` en retour
(règle absolue, doc 03 §3).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from axelcompta.core.errors import DomaineError
from axelcompta.core.ids import EcritureId
from axelcompta.core.money import Money
from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

from .providers.base import NormalizedTransaction, PlatformSettlement

TAUX_TVA_RECETTES_DEMO = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class TemplateCommissionTVA:
    """doc 13 §5.2 : la TVA sur commission dépend de l'entité facturante."""

    taux: Decimal
    autoliquidation: bool


TEMPLATES_COMMISSION = {
    "france_20": TemplateCommissionTVA(taux=Decimal("0.20"), autoliquidation=False),
    "autoliquidation_ue": TemplateCommissionTVA(taux=Decimal("0.20"), autoliquidation=True),
}


class RegimeTvaInconnu(DomaineError):
    """`commission_tva_regime` sans template (doc 13 §5.2) — erreur attendue :
    un nouveau régime s'ajoute en données, ne se devine jamais (doc 08 §5)."""


def _ventiler(montant_ttc_cts: int, taux: Decimal) -> tuple[int, int]:
    """(HT, TVA) tels que HT + TVA == montant_ttc_cts exactement — aucune
    perte au centime, tout l'arrondi porte sur la TVA."""
    ht = int(
        (Decimal(montant_ttc_cts) / (Decimal(1) + taux)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    return ht, montant_ttc_cts - ht


def _lignes_commission(
    settlement: PlatformSettlement,
    template: TemplateCommissionTVA,
    recettes_ht: int,
    tva_collectee: int,
) -> list[LigneEcriture]:
    if template.autoliquidation:
        # déjà HT, pas de TVA facturée par la plateforme (Bolt, doc 13 §5.3)
        commission_ht = settlement.commission_cts
        tva_autoliq = int(
            (Decimal(commission_ht) * template.taux).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        return [
            LigneEcriture("622", Sens.DEBIT, Money(commission_ht)),
            LigneEcriture("44566", Sens.DEBIT, Money(tva_autoliq), code_tva="autoliquidation"),
            LigneEcriture("706", Sens.CREDIT, Money(recettes_ht)),
            LigneEcriture("44571", Sens.CREDIT, Money(tva_collectee)),
            LigneEcriture("44571", Sens.CREDIT, Money(tva_autoliq), code_tva="autoliquidation"),
        ]
    commission_ht, tva_commission = _ventiler(settlement.commission_cts, template.taux)
    return [
        LigneEcriture("622", Sens.DEBIT, Money(commission_ht)),
        LigneEcriture("44566", Sens.DEBIT, Money(tva_commission)),
        LigneEcriture("706", Sens.CREDIT, Money(recettes_ht)),
        LigneEcriture("44571", Sens.CREDIT, Money(tva_collectee)),
    ]


def construire_ecriture_settlement(
    transaction: NormalizedTransaction, settlement: PlatformSettlement, numero: int
) -> Ecriture:
    """doc 13 §5.3. Le montant du 512 est celui du settlement
    (`net_payout_cts`), pas celui de la transaction bancaire : les deux
    peuvent différer d'1 centime (tolérance de réconciliation, doc 13 §4.2)
    et seul le premier garantit l'équilibre avec les lignes dérivées.
    """
    template = TEMPLATES_COMMISSION.get(settlement.commission_tva_regime)
    if template is None:
        raise RegimeTvaInconnu(settlement.commission_tva_regime)

    recettes_ht, tva_collectee = _ventiler(settlement.gross_earnings_cts, TAUX_TVA_RECETTES_DEMO)
    lignes = [
        LigneEcriture("512", Sens.DEBIT, Money(settlement.net_payout_cts)),
        *_lignes_commission(settlement, template, recettes_ht, tva_collectee),
    ]
    return Ecriture(
        id=EcritureId(f"settlement-{numero}"),
        dossier_id=transaction.dossier_id,
        journal=Journal.BQ,
        date=transaction.date,
        libelle=f"Règlement {settlement.platform} — {transaction.libelle}",
        reference_piece=None,
        lignes=tuple(lignes),
    )
