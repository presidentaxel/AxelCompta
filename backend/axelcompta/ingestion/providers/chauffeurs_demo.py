"""Générateur de données synthétiques mais réalistes pour 3 chauffeurs type
(doc 17 §4, doc 19) — remplace le replay du CSV audit comme source de la
démo produit (pivot 2026-09-06) : un chauffeur type par régime/plateforme à
tester, fabriqué à la main pour être crédible, pas du bruit réel plein
d'aléas (doc 17 §2).

Volumétrie demandée par Louis (2026-09-06) : jusqu'à 5-6 courses/jour, sur
~200 jours d'activité, avec pourboires. **Les courses ne sont pas
comptabilisées une par une** : Rollee ne remonte à la compta que des
relevés agrégés (doc 13 §3.2 — `trips` = granularité d'audit, `income` /
settlement = la donnée comptable), donc les courses générées ici servent
uniquement à calculer des `PlatformSettlement` hebdomadaires réalistes
(volume, variabilité), la seule granularité que le moteur consomme
(doc 13 §4.1). Simplification assumée (doc 17 §2, « pas de cas limites ») :
les pourboires sont inclus dans le brut de la plateforme avant calcul de
commission, comme le reste de la course — dans la réalité, certaines
plateformes ne prennent pas de commission sur les pourboires.

Génération déterministe (`random.Random(graine)` par profil) : reproductible
d'un run à l'autre, aucun fichier externe requis (contrairement au CSV audit
gitignored dont dépendent `demo_dossier_reel.py`/`demo_multi_dossiers.py`) —
ce module tourne sur n'importe quel clone du repo.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from axelcompta.core.ids import DossierId, TenantId, TransactionId

from .base import DataProvider, NormalizedTransaction, PlatformSettlement, ProviderHealth


@dataclass(frozen=True, slots=True)
class ConfigPlateforme:
    """Une plateforme utilisée par un profil (doc 13 §5.2 : le régime TVA de
    la commission dépend de l'entité facturante, pas du chauffeur)."""

    nom: str  # "uber" | "bolt" — doit apparaître dans le libellé bancaire (doc 13 §4.2)
    libelle_bancaire: str
    commission_tva_regime: str  # "france_20" | "autoliquidation_ue" (doc 13 §5.2)
    taux_commission: Decimal  # part du brut prélevée par la plateforme
    poids: float  # proportion des courses sur cette plateforme si plusieurs coexistent


@dataclass(frozen=True, slots=True)
class DepenseRecurrente:
    """Une charge qui revient à intervalle régulier (carburant, télécom...)."""

    libelle: str
    montant_cts: tuple[int, int]  # (min, max), bornes incluses
    frequence_jours: int  # tous les N jours calendaires en moyenne


@dataclass(frozen=True, slots=True)
class DepensePonctuelle:
    """Une charge unique — sert au cas Sophie (doc 17 §4.2 : dépense perso
    ambiguë à trancher en file de revue, pas un cas limite récurrent)."""

    libelle: str
    montant_cts: int
    jour_relatif: int  # nombre de jours depuis `date_debut` du profil


@dataclass(frozen=True, slots=True)
class ProfilChauffeurType:
    """Un chauffeur type (doc 17 §4, doc 19) — ce qui varie d'un profil à
    l'autre ; la génération et l'agrégation sont partagées (fonctions
    ci-dessous)."""

    dossier_id: DossierId
    nom: str  # pour les logs/rapports uniquement — jamais une vraie donnée personnelle
    tva_recettes_regime: str  # "assujetti_taux_reduit" | "franchise" (doc 14 §1.2)
    plateformes: tuple[ConfigPlateforme, ...]
    date_debut: date
    nb_jours_actifs: int
    graine: int
    courses_par_jour: tuple[int, int] = (2, 6)  # Louis (2026-09-06) : « jusqu'à 5/6 »
    prix_course_cts: tuple[int, int] = (9_00, 25_00)
    probabilite_pourboire: float = 0.18
    pourboire_cts: tuple[int, int] = (1_00, 5_00)
    depenses_recurrentes: tuple[DepenseRecurrente, ...] = field(default_factory=tuple)
    depense_ponctuelle: DepensePonctuelle | None = None


def _debut_semaine(jour: date) -> date:
    return jour - timedelta(days=jour.weekday())  # lundi


def _generer_courses(
    profil: ProfilChauffeurType, rng: random.Random
) -> tuple[list[tuple[date, ConfigPlateforme, int, int]], date]:
    """Retourne (courses, date_fin) — `date_fin` est le lendemain du dernier
    jour actif, sert de borne calendaire aux dépenses récurrentes (§ci-dessous)."""
    courses: list[tuple[date, ConfigPlateforme, int, int]] = []
    jour = profil.date_debut
    jours_actifs = 0
    plateformes = list(profil.plateformes)
    poids = [p.poids for p in plateformes]
    while jours_actifs < profil.nb_jours_actifs:
        if rng.random() < 1 / 7:  # ~1 jour de repos par semaine, pas forcément le même
            jour += timedelta(days=1)
            continue
        for _ in range(rng.randint(*profil.courses_par_jour)):
            plateforme = rng.choices(plateformes, weights=poids, k=1)[0]
            montant = rng.randint(*profil.prix_course_cts)
            pourboire = (
                rng.randint(*profil.pourboire_cts)
                if rng.random() < profil.probabilite_pourboire
                else 0
            )
            courses.append((jour, plateforme, montant, pourboire))
        jours_actifs += 1
        jour += timedelta(days=1)
    return courses, jour


def _construire_settlements(
    profil: ProfilChauffeurType, courses: list[tuple[date, ConfigPlateforme, int, int]]
) -> tuple[PlatformSettlement, ...]:
    brut_par_semaine: dict[tuple[date, str], int] = {}
    courses_par_semaine: dict[tuple[date, str], int] = {}
    for jour, plateforme, montant, pourboire in courses:
        cle = (_debut_semaine(jour), plateforme.nom)
        brut_par_semaine[cle] = brut_par_semaine.get(cle, 0) + montant + pourboire
        courses_par_semaine[cle] = courses_par_semaine.get(cle, 0) + 1

    plateforme_par_nom = {p.nom: p for p in profil.plateformes}
    settlements = []
    for debut_semaine, nom_plateforme in sorted(brut_par_semaine):
        brut = brut_par_semaine[(debut_semaine, nom_plateforme)]
        plateforme = plateforme_par_nom[nom_plateforme]
        fin_semaine = debut_semaine + timedelta(days=6)
        payout_date = fin_semaine + timedelta(days=2)
        commission = int(
            (Decimal(brut) * plateforme.taux_commission).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        settlements.append(
            PlatformSettlement(
                dossier_id=profil.dossier_id,
                platform=nom_plateforme,
                period_start=debut_semaine,
                period_end=fin_semaine,
                payout_date=payout_date,
                gross_earnings_cts=brut,
                commission_cts=commission,
                commission_tva_regime=plateforme.commission_tva_regime,
                net_payout_cts=brut - commission,
                currency="EUR",
                source_provider="chauffeur_type",
                raw_payload={"nb_courses": courses_par_semaine[(debut_semaine, nom_plateforme)]},
            )
        )
    return tuple(settlements)


def _transactions_settlements(
    profil: ProfilChauffeurType, settlements: tuple[PlatformSettlement, ...]
) -> list[NormalizedTransaction]:
    plateforme_par_nom = {p.nom: p for p in profil.plateformes}
    return [
        NormalizedTransaction(
            id=TransactionId(f"{profil.dossier_id}-settlement-{settlement.platform}-{i}"),
            dossier_id=profil.dossier_id,
            date=settlement.payout_date + timedelta(days=1),  # virement reçu le lendemain
            montant_cts=settlement.net_payout_cts,
            libelle=plateforme_par_nom[settlement.platform].libelle_bancaire,
            source_provider="chauffeur_type",
            raw_payload={},
        )
        for i, settlement in enumerate(settlements, start=1)
    ]


def _transactions_depenses(
    profil: ProfilChauffeurType, rng: random.Random, date_fin: date
) -> list[NormalizedTransaction]:
    transactions = []
    for depense in profil.depenses_recurrentes:
        jour = profil.date_debut
        compteur = 0
        id_base = f"{profil.dossier_id}-depense-{depense.libelle}".replace(" ", "_")
        while jour < date_fin:
            transactions.append(
                NormalizedTransaction(
                    id=TransactionId(f"{id_base}-{compteur}"),
                    dossier_id=profil.dossier_id,
                    date=jour,
                    montant_cts=-rng.randint(*depense.montant_cts),
                    libelle=depense.libelle,
                    source_provider="chauffeur_type",
                    raw_payload={},
                )
            )
            compteur += 1
            jour += timedelta(days=depense.frequence_jours)
    if profil.depense_ponctuelle is not None:
        d = profil.depense_ponctuelle
        transactions.append(
            NormalizedTransaction(
                id=TransactionId(f"{profil.dossier_id}-depense-ponctuelle"),
                dossier_id=profil.dossier_id,
                date=profil.date_debut + timedelta(days=d.jour_relatif),
                montant_cts=-d.montant_cts,
                libelle=d.libelle,
                source_provider="chauffeur_type",
                raw_payload={},
            )
        )
    return transactions


class ChauffeurTypeProvider(DataProvider):
    """Un provider par profil — génère au chargement (une fois, mis en cache
    sur l'instance), comme un vrai provider mettrait en cache un appel API
    coûteux. Implémente le même contrat `DataProvider` (doc 13 §2.2) que les
    providers réels : rien d'autre dans le pipeline ne sait que les données
    sont synthétiques (doc 03 §3bis)."""

    def __init__(self, profil: ProfilChauffeurType) -> None:
        self._profil = profil
        rng = random.Random(profil.graine)
        courses, date_fin = _generer_courses(profil, rng)
        self._settlements = _construire_settlements(profil, courses)
        transactions = _transactions_settlements(profil, self._settlements)
        transactions += _transactions_depenses(profil, rng, date_fin)
        self._transactions = tuple(sorted(transactions, key=lambda t: t.date))

    async def fetch_transactions(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[NormalizedTransaction]:
        return [t for t in self._transactions if since <= t.date <= until]

    async def fetch_platform_settlements(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[PlatformSettlement]:
        return [s for s in self._settlements if since <= s.payout_date <= until]

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            ok=True, message=f"chauffeur type ({self._profil.nom}) : données synthétiques"
        )


# --- Les 3 profils (doc 17 §4) ------------------------------------------

_UBER = ConfigPlateforme(
    nom="uber",
    libelle_bancaire="VIR UBER BV AMSTERDAM",
    commission_tva_regime="france_20",
    # Ratio du golden test doc 13 §5.3 (192,00 / 1 040,00) appliqué à toutes
    # les semaines plutôt qu'un seul règlement — même entité facturante.
    taux_commission=Decimal("0.1846"),
    poids=1.0,
)
_BOLT = ConfigPlateforme(
    nom="bolt",
    libelle_bancaire="VIR BOLT OPERATIONS OU",
    commission_tva_regime="autoliquidation_ue",
    taux_commission=Decimal("0.15"),  # commission_cts déjà HT pour l'autoliquidation
    poids=1.0,
)

PROFIL_KARIM = ProfilChauffeurType(
    dossier_id=DossierId("DEMO_karim"),
    nom="Karim",
    tva_recettes_regime="assujetti_taux_reduit",
    plateformes=(_UBER,),
    date_debut=date(2025, 1, 6),
    nb_jours_actifs=200,
    graine=1001,
    courses_par_jour=(3, 6),
    depenses_recurrentes=(
        DepenseRecurrente("CB TOTAL ACCESS A6", (55_00, 72_00), 4),
        DepenseRecurrente("COFIROUTE A10", (6_00, 14_00), 5),
        DepenseRecurrente("CB MCDONALD'S", (7_00, 13_00), 6),  # repas légitime, doc 07 §4
        DepenseRecurrente("PRLV MAAF ASSURANCE AUTO", (68_00, 68_00), 30),
        DepenseRecurrente("SFR MOBILE", (22_00, 22_00), 30),
        DepenseRecurrente("NORAUTO ENTRETIEN", (45_00, 130_00), 70),
    ),
)

PROFIL_SOPHIE = ProfilChauffeurType(
    dossier_id=DossierId("DEMO_sophie"),
    nom="Sophie",
    tva_recettes_regime="assujetti_taux_reduit",
    plateformes=(replace(_UBER, poids=0.55), replace(_BOLT, poids=0.45)),
    date_debut=date(2025, 1, 6),
    nb_jours_actifs=200,
    graine=1002,
    courses_par_jour=(2, 6),
    depenses_recurrentes=(
        DepenseRecurrente("CB TOTAL ACCESS A6", (55_00, 72_00), 4),
        DepenseRecurrente("COFIROUTE A10", (6_00, 14_00), 5),
        DepenseRecurrente("CB MCDONALD'S", (7_00, 13_00), 6),
        DepenseRecurrente("PRLV AXA ASSURANCE AUTO", (72_00, 72_00), 30),
        DepenseRecurrente("BOUYGUES TELECOM", (20_00, 20_00), 30),
        DepenseRecurrente("MIDAS ENTRETIEN", (40_00, 120_00), 70),
    ),
    # doc 17 §4.2 : dépense carte pro à consonance personnelle, à trancher en
    # file de revue humaine — pas auto-acceptée (doc 17 §11 golden test).
    depense_ponctuelle=DepensePonctuelle("CB ZARA FRANCE", 68_00, jour_relatif=95),
)

PROFIL_YANIS = ProfilChauffeurType(
    dossier_id=DossierId("DEMO_yanis"),
    nom="Yanis",
    tva_recettes_regime="franchise",
    # Uber uniquement (pas Bolt) : le régime franchise n'est câblé côté
    # écritures que pour une commission `france_20` (doc 13 §5.3, doc 17
    # §4.3) — combiner franchise + autoliquidation UE (Bolt) est un vrai
    # sujet fiscal volontairement laissé hors scope démo.
    plateformes=(_UBER,),
    date_debut=date(2025, 1, 6),
    nb_jours_actifs=200,
    graine=1003,
    courses_par_jour=(2, 5),
    depenses_recurrentes=(
        DepenseRecurrente("CB TOTAL ACCESS A6", (55_00, 72_00), 4),
        DepenseRecurrente("COFIROUTE A10", (6_00, 14_00), 6),
        DepenseRecurrente("PRLV MATMUT ASSURANCE AUTO", (65_00, 65_00), 30),
        # doc 06 §3.5 : véhicule financé en LOA plutôt qu'acheté — le pack
        # réduit initial n'avait pas de règle pour ça (ajoutée, doc 17 §4.3).
        DepenseRecurrente("PRLV ALD AUTOMOTIVE LOA", (378_00, 378_00), 30),
    ),
)

PROFILS_DEMO: tuple[ProfilChauffeurType, ...] = (PROFIL_KARIM, PROFIL_SOPHIE, PROFIL_YANIS)
