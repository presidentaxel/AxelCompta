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
commission, comme le reste de la course.

Poussé plus loin le 2026-09-06 (« on connaît les chiffres, autant pousser
un peu ») : montée en charge progressive en début de période, congés,
plusieurs dépenses ponctuelles par profil (pas une seule anecdote),
renouvellement de contrat en cours d'année (LOA de Yanis), et un règlement
dont le virement arrive hors fenêtre de réconciliation (doc 13 §4.2/§4.3,
§6 « mode dégradé ») — un dossier par ailleurs propre peut quand même avoir
un accroc, exactement ce que la réconciliation réelle doit savoir reporter.

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

JOURS_MONTEE_EN_CHARGE = 30  # jours actifs de montée en charge (doc 17, réalisme)


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
    """Une charge qui revient à intervalle régulier. `debut_relatif`/
    `fin_relatif` (jours depuis `date_debut` du profil, `fin_relatif=None` =
    jusqu'à la fin) permettent un changement en cours d'année (ex. Yanis :
    renouvellement de LOA avec un nouveau loueur et un nouveau montant)."""

    libelle: str
    montant_cts: tuple[int, int]  # (min, max), bornes incluses
    frequence_jours: int  # tous les N jours calendaires en moyenne
    debut_relatif: int = 0
    fin_relatif: int | None = None


@dataclass(frozen=True, slots=True)
class DepensePonctuelle:
    """Une charge unique — dépense ambiguë à trancher (doc 17 §4.2) ou
    incident isolé (amende, grosse réparation) : pas un cas limite
    récurrent, mais pas plus rare qu'une seule fois par dossier non plus."""

    libelle: str
    montant_cts: int
    jour_relatif: int  # nombre de jours depuis `date_debut` du profil


@dataclass(frozen=True, slots=True)
class Conges:
    """Un bloc de jours sans aucune course (vacances, arrêt) — pas juste le
    bruit aléatoire d'1 jour de repos sur 7."""

    debut_relatif: int
    duree_jours: int


@dataclass(frozen=True, slots=True)
class RetardReglement:
    """Un règlement précis dont le virement bancaire arrive hors fenêtre de
    réconciliation (doc 13 §4.2 : [-3j, +5j] autour du `payout_date`) — sert
    à exercer l'état `en_attente_banque` et le mode dégradé (doc 13 §4.3,
    §6) sur un dossier par ailleurs propre, plutôt qu'un pipeline qui ne
    connaît que le cas parfait."""

    plateforme: str
    index_settlement: int  # index (0-based) parmi les settlements de cette plateforme
    retard_jours: int  # doit dépasser +5j pour rater sa propre fenêtre


@dataclass(frozen=True, slots=True)
class ProfilChauffeurType:
    """Un chauffeur type (doc 17 §4, doc 19) — ce qui varie d'un profil à
    l'autre ; la génération et l'agrégation sont partagées (fonctions
    ci-dessous)."""

    dossier_id: DossierId
    nom: str  # pour les logs/rapports uniquement — jamais une vraie donnée personnelle
    tva_recettes_regime: str  # "assujetti_taux_reduit" | "franchise" (doc 14 §1.2)
    forme_juridique: str  # "SASU" | "EURL" (doc 06 §7) — détermine le compte usage personnel
    plateformes: tuple[ConfigPlateforme, ...]
    date_debut: date
    nb_jours_actifs: int
    graine: int
    # "gestionnaire" | "chauffeur_direct" (doc 19 §4) — qui connecte la
    # banque. Défaut "gestionnaire" : c'est le cas pilote actuel.
    mode_acces_bancaire: str = "gestionnaire"
    courses_par_jour: tuple[int, int] = (2, 6)  # Louis (2026-09-06) : « jusqu'à 5/6 »
    prix_course_cts: tuple[int, int] = (9_00, 25_00)
    probabilite_pourboire: float = 0.18
    pourboire_cts: tuple[int, int] = (1_00, 5_00)
    depenses_recurrentes: tuple[DepenseRecurrente, ...] = field(default_factory=tuple)
    depenses_ponctuelles: tuple[DepensePonctuelle, ...] = field(default_factory=tuple)
    conges: tuple[Conges, ...] = field(default_factory=tuple)
    retard_reglement: RetardReglement | None = None


def _debut_semaine(jour: date) -> date:
    return jour - timedelta(days=jour.weekday())  # lundi


def _en_conges(jour: date, profil: ProfilChauffeurType) -> bool:
    return any(
        profil.date_debut + timedelta(days=c.debut_relatif)
        <= jour
        < profil.date_debut + timedelta(days=c.debut_relatif + c.duree_jours)
        for c in profil.conges
    )


def _bornes_du_jour(profil: ProfilChauffeurType, jours_actifs_deja: int) -> tuple[int, int]:
    """Montée en charge : les `JOURS_MONTEE_EN_CHARGE` premiers jours actifs
    ont un plafond de courses réduit, converge ensuite vers la fourchette
    nominale du profil — un chauffeur qui démarre ne fait pas tout de suite
    son plein volume."""
    mini, maxi = profil.courses_par_jour
    if jours_actifs_deja >= JOURS_MONTEE_EN_CHARGE:
        return mini, maxi
    facteur = 0.5 + 0.5 * (jours_actifs_deja / JOURS_MONTEE_EN_CHARGE)
    maxi_reduit = max(mini, round(mini + (maxi - mini) * facteur))
    return mini, maxi_reduit


def _generer_courses(
    profil: ProfilChauffeurType, rng: random.Random
) -> tuple[list[tuple[date, ConfigPlateforme, int, int]], date]:
    """Retourne (courses, date_fin) — `date_fin` est le lendemain du dernier
    jour actif, sert de borne calendaire par défaut aux dépenses récurrentes."""
    courses: list[tuple[date, ConfigPlateforme, int, int]] = []
    jour = profil.date_debut
    jours_actifs = 0
    plateformes = list(profil.plateformes)
    poids = [p.poids for p in plateformes]
    while jours_actifs < profil.nb_jours_actifs:
        if _en_conges(jour, profil) or rng.random() < 1 / 7:  # + ~1 jour de repos/semaine
            jour += timedelta(days=1)
            continue
        for _ in range(rng.randint(*_bornes_du_jour(profil, jours_actifs))):
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
    """Virement reçu le lendemain du `payout_date`, sauf le règlement visé
    par `profil.retard_reglement` (§ci-dessus) : son virement arrive après
    la fenêtre de réconciliation (doc 13 §4.2), volontairement."""
    plateforme_par_nom = {p.nom: p for p in profil.plateformes}
    compteur_par_plateforme: dict[str, int] = {}
    transactions = []
    for i, settlement in enumerate(settlements, start=1):
        index_plateforme = compteur_par_plateforme.get(settlement.platform, 0)
        compteur_par_plateforme[settlement.platform] = index_plateforme + 1
        retard = profil.retard_reglement
        delai = (
            retard.retard_jours
            if retard is not None
            and retard.plateforme == settlement.platform
            and retard.index_settlement == index_plateforme
            else 1
        )
        transactions.append(
            NormalizedTransaction(
                id=TransactionId(f"{profil.dossier_id}-settlement-{settlement.platform}-{i}"),
                dossier_id=profil.dossier_id,
                date=settlement.payout_date + timedelta(days=delai),
                montant_cts=settlement.net_payout_cts,
                libelle=plateforme_par_nom[settlement.platform].libelle_bancaire,
                source_provider="chauffeur_type",
                raw_payload={},
            )
        )
    return transactions


def _transactions_recurrentes(
    profil: ProfilChauffeurType, rng: random.Random, date_fin_defaut: date
) -> list[NormalizedTransaction]:
    transactions = []
    for depense in profil.depenses_recurrentes:
        jour = profil.date_debut + timedelta(days=depense.debut_relatif)
        fin = (
            profil.date_debut + timedelta(days=depense.fin_relatif)
            if depense.fin_relatif is not None
            else date_fin_defaut
        )
        id_base = f"{profil.dossier_id}-depense-{depense.libelle}-{depense.debut_relatif}"
        id_base = id_base.replace(" ", "_")
        compteur = 0
        while jour < fin:
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
    return transactions


def _transactions_ponctuelles(profil: ProfilChauffeurType) -> list[NormalizedTransaction]:
    return [
        NormalizedTransaction(
            id=TransactionId(f"{profil.dossier_id}-depense-ponctuelle-{i}"),
            dossier_id=profil.dossier_id,
            date=profil.date_debut + timedelta(days=d.jour_relatif),
            montant_cts=-d.montant_cts,
            libelle=d.libelle,
            source_provider="chauffeur_type",
            raw_payload={},
        )
        for i, d in enumerate(profil.depenses_ponctuelles)
    ]


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
        transactions += _transactions_recurrentes(profil, rng, date_fin)
        transactions += _transactions_ponctuelles(profil)
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
    forme_juridique="SASU",  # doc 17 §4.1
    plateformes=(_UBER,),
    date_debut=date(2025, 1, 6),
    nb_jours_actifs=200,
    graine=1001,
    # doc 17 §6/§7 : Karim est le profil retenu pour le parcours chauffeur
    # (connexion bancaire directe visible) — Sophie/Yanis restent en mode
    # gestionnaire (cas pilote), les deux modes sont donc représentés.
    mode_acces_bancaire="chauffeur_direct",
    courses_par_jour=(3, 6),
    depenses_recurrentes=(
        DepenseRecurrente("CB TOTAL ACCESS A6", (55_00, 72_00), 4),
        DepenseRecurrente("COFIROUTE A10", (6_00, 14_00), 5),
        DepenseRecurrente("CB MCDONALD'S", (7_00, 13_00), 6),  # repas légitime, doc 07 §4
        DepenseRecurrente("PRLV MAAF ASSURANCE AUTO", (68_00, 68_00), 30),
        DepenseRecurrente("SFR MOBILE", (22_00, 22_00), 30),
        DepenseRecurrente("NORAUTO ENTRETIEN", (45_00, 130_00), 70),
        DepenseRecurrente("PRLV URSSAF", (950_00, 1_250_00), 91),  # trimestriel
        DepenseRecurrente("VIR EXPERT COMPTABLE DUPONT", (280_00, 280_00), 182),  # semestriel
    ),
    depenses_ponctuelles=(
        DepensePonctuelle("AMENDE.GOUV.FR", 68_00, jour_relatif=60),
        # grosse panne, pas la routine entretien ci-dessus (doc 17, « pousser »)
        DepensePonctuelle("NORAUTO REPARATION MOTEUR", 890_00, jour_relatif=140),
    ),
    conges=(Conges(debut_relatif=170, duree_jours=9),),  # coupure estivale
    # Un règlement par ailleurs propre qui n'arrive pas dans les temps —
    # exerce en_attente_banque + mode dégradé (doc 13 §4.3/§6) sur le
    # profil « simple », pas seulement sur un cas construit pour ça.
    retard_reglement=RetardReglement(plateforme="uber", index_settlement=14, retard_jours=9),
)

PROFIL_SOPHIE = ProfilChauffeurType(
    dossier_id=DossierId("DEMO_sophie"),
    nom="Sophie",
    tva_recettes_regime="assujetti_taux_reduit",
    forme_juridique="EURL",  # doc 17 §4.2
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
        DepenseRecurrente("PRLV URSSAF", (1_050_00, 1_350_00), 91),
        DepenseRecurrente("VIR EXPERT COMPTABLE MARTIN", (310_00, 310_00), 182),
    ),
    # doc 17 §4.2 : plusieurs dépenses ambiguës sur l'année, pas une seule
    # anecdote — le but est de voir la file de revue avec du volume dessus.
    depenses_ponctuelles=(
        DepensePonctuelle("CB ZARA FRANCE", 68_00, jour_relatif=55),
        DepensePonctuelle("AMENDE.GOUV.FR", 45_00, jour_relatif=95),
        DepensePonctuelle("CB FNAC PARIS", 129_00, jour_relatif=130),
        DepensePonctuelle("CB SEPHORA", 54_00, jour_relatif=185),
    ),
    conges=(Conges(debut_relatif=150, duree_jours=7),),
)

PROFIL_YANIS = ProfilChauffeurType(
    dossier_id=DossierId("DEMO_yanis"),
    nom="Yanis",
    tva_recettes_regime="franchise",
    # Non précisé dans doc 17 §4.3 — assumé pour compléter le champ, sans
    # impact sur la démo actuelle (Yanis ne passe jamais par la revue
    # humaine/usage personnel, doc 17 §11). À confirmer avec Louis si un
    # jour Yanis a besoin de ce compte.
    forme_juridique="SASU",
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
        DepenseRecurrente("PRLV URSSAF", (700_00, 950_00), 91),
        DepenseRecurrente("VIR EXPERT COMPTABLE LEROY", (260_00, 260_00), 182),
        # Renouvellement de contrat en cours d'année, pas juste un montant
        # fixe sur toute la période (doc 06 §3.5, doc 17 §4.3) : premier
        # loueur jusqu'au jour 180, nouveau loueur/montant ensuite — les deux
        # matchent la même règle du pack (`\bald\b|arval|...`).
        DepenseRecurrente("PRLV ALD AUTOMOTIVE LOA", (378_00, 378_00), 30, fin_relatif=180),
        DepenseRecurrente(
            "PRLV ARVAL LOCATION LOA", (410_00, 410_00), 30, debut_relatif=180
        ),
    ),
    depenses_ponctuelles=(DepensePonctuelle("AMENDE.GOUV.FR", 90_00, jour_relatif=100),),
    conges=(Conges(debut_relatif=120, duree_jours=8),),
)

PROFILS_DEMO: tuple[ProfilChauffeurType, ...] = (PROFIL_KARIM, PROFIL_SOPHIE, PROFIL_YANIS)
