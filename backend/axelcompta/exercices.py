"""Passage d'un dossier à l'exercice suivant (doc 06 §2, §5, §7).

Composition root, comme `taches.py`. Deux temps :
1. `preparer_passage` ne touche à rien : vérifie que l'exercice est terminé
   et qu'aucune opération n'attend de décision, calcule les écritures
   d'inventaire (TVA, IS), l'écriture d'à-nouveaux et la configuration du
   nouvel exercice (avenant de régime en vigueur, sortie de la franchise de
   TVA si le seuil de base a été dépassé) ;
2. `executer_passage` l'écrit : écritures en base (append-only), exercice
   clos dans l'historique, dossier ouvert sur le nouvel exercice.

L'exécution est rejouable : si elle s'interrompt, la relancer n'ajoute ni
écriture ni exercice en double (identifiants stables) et termine le travail.
Rien ne la déclenche seul : la décision de clore reste humaine (doc 06 §5,
doc 19 §5.3), par la ligne de commande ci-dessous.

Usage, depuis backend/ (DATABASE_URL défini) :

    python -m axelcompta.exercices --dossier <dossier_id>             # simulation
    python -m axelcompta.exercices --dossier <dossier_id> --executer

Le portefeuille de démo est refusé à l'exécution sans `--y-compris-demo` :
le menu Démo ne sait pas effacer des à-nouveaux (verrouillés en base).
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from axelcompta.closing.cloture_fiscale import (
    chiffre_affaires_ht,
    ecritures_de_cloture,
    ecritures_exercice,
    hors_inventaire,
)
from axelcompta.closing.models import ParametresCloture
from axelcompta.closing.ouverture import ecriture_a_nouveaux
from axelcompta.core.db import engine_depuis_env
from axelcompta.core.ids import DossierId
from axelcompta.demo_seed import TENANT_DEMO
from axelcompta.ledger.models import Ecriture
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.ledger.service import LedgerService
from axelcompta.packs.vtc_demo import charger_compte_par_categorie
from axelcompta.tenants.avenants import AvenantRegime, regime_pour_exercice
from axelcompta.tenants.avenants_postgres import PostgresAvenantRegimeRepository
from axelcompta.tenants.exercices import ExerciceClos, ExerciceDejaClos, ExerciceRepository
from axelcompta.tenants.exercices_postgres import PostgresExerciceRepository
from axelcompta.tenants.franchise_tva import EtatFranchise, MillesimeInconnu, suivre_franchise
from axelcompta.tenants.models import Dossier
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.tenants.repository import DossierRepository
from axelcompta.tenants.statuts import RegimeTva, configuration_de
from axelcompta.workflow.decisions import DecisionRepository
from axelcompta.workflow.decisions_postgres import PostgresDecisionRepository
from axelcompta.workflow.notifications import ecritures_a_trancher
from axelcompta.workflow.revue import appliquer_decisions


class PassageRefuse(ValueError):
    """L'exercice ne peut pas être clos maintenant ; le message dit pourquoi."""


@dataclass(frozen=True, slots=True)
class PassageExercice:
    avant: Dossier
    apres: Dossier
    ecritures: tuple[Ecriture, ...]  # inventaire puis à-nouveaux, à ajouter
    changements: tuple[str, ...]


def preparer_passage(
    dossier: Dossier,
    ledger: LedgerService,
    decisions: DecisionRepository,
    avenants: tuple[AvenantRegime, ...],
    aujourd_hui: date,
) -> PassageExercice:
    fin = dossier.fin_exercice()
    if fin >= aujourd_hui:
        raise PassageRefuse(f"l'exercice se termine le {fin:%d/%m/%Y}, il n'est pas terminé")
    en_attente = ecritures_a_trancher(ledger, decisions, dossier.id)
    if en_attente:
        raise PassageRefuse(f"{len(en_attente)} opération(s) attendent encore une décision")
    colonne = configuration_de(dossier).colonne
    tranchees = appliquer_decisions(
        ledger.grand_livre(dossier.id),
        decisions.lister_decisions(dossier.id),
        colonne.compte_usage_personnel,
        charger_compte_par_categorie(),
    )
    parametres = ParametresCloture(
        exercice_debut=dossier.exercice_debut,
        exercice_fin=fin,
        forme_juridique=dossier.forme_juridique,
        identite=dossier.identite,
        soumis_is=colonne.soumis_is,
        associes=colonne.associes,
    )
    de_l_exercice = hors_inventaire(
        dossier.id, ecritures_exercice(tranchees, parametres), parametres
    )
    inventaire = ecritures_de_cloture(dossier.id, de_l_exercice, parametres)
    ouverture = fin + timedelta(days=1)
    a_nouveaux = ecriture_a_nouveaux(dossier.id, de_l_exercice + inventaire, ouverture)
    apres, changements = _configuration_suivante(dossier, avenants, tranchees, ouverture)
    configuration_de(apres)
    ecritures = inventaire + ((a_nouveaux,) if a_nouveaux else ())
    return PassageExercice(dossier, apres, ecritures, changements)


def _configuration_suivante(
    dossier: Dossier,
    avenants: tuple[AvenantRegime, ...],
    ecritures: tuple[Ecriture, ...],
    ouverture: date,
) -> tuple[Dossier, tuple[str, ...]]:
    changements: list[str] = []
    regime, option = regime_pour_exercice(dossier, avenants, ouverture.year)
    if regime != dossier.regime_imposition:
        changements.append(f"régime d'imposition : {dossier.regime_imposition} → {regime}")
    regime_tva, recettes = dossier.regime_tva, dossier.tva_recettes_regime
    if configuration_de(dossier).regime_tva is RegimeTva.FRANCHISE:
        annee = ouverture.year - 1
        try:
            suivi = suivre_franchise(chiffre_affaires_ht(ecritures, annee), annee)
        except MillesimeInconnu as exc:
            raise PassageRefuse(str(exc)) from exc
        if suivi.etat in (EtatFranchise.SEUIL_BASE_DEPASSE, EtatFranchise.SEUIL_MAJORE_DEPASSE):
            regime_tva, recettes = RegimeTva.REEL_NORMAL.value, "assujetti_taux_reduit"
            changements.append("TVA : sortie de la franchise en base, réel normal")
    apres = dataclasses.replace(
        dossier,
        exercice_debut=ouverture,
        exercice_fin=None,
        regime_imposition=regime,
        option_ir_debut=option,
        regime_tva=regime_tva,
        tva_recettes_regime=recettes,
    )
    return apres, tuple(changements)


def executer_passage(
    passage: PassageExercice,
    ledger: LedgerService,
    dossiers: DossierRepository,
    exercices: ExerciceRepository,
    maintenant: datetime,
    auteur: str,
) -> None:
    avant = passage.avant
    deja = {e.id for e in ledger.grand_livre(avant.id)}
    for ecriture in passage.ecritures:
        if ecriture.id not in deja:
            ledger.enregistrer(ecriture)
    try:
        exercices.enregistrer(
            ExerciceClos(
                dossier_id=avant.id,
                debut=avant.exercice_debut,
                fin=avant.fin_exercice(),
                clos_le=maintenant,
                clos_par=auteur,
                changements=passage.changements,
            )
        )
    except ExerciceDejaClos:
        pass  # reprise après une interruption : l'historique est déjà là
    dossiers.ouvrir_exercice(passage.apres)


def _afficher(passage: PassageExercice) -> None:
    avant, apres = passage.avant, passage.apres
    print(f"{avant.id} : exercice {avant.exercice_debut} → {avant.fin_exercice()} à clore")
    for ecriture in passage.ecritures:
        print(f"  écriture {ecriture.reference_piece} ({len(ecriture.lignes)} lignes)")
    print(f"  nouvel exercice à partir du {apres.exercice_debut}")
    for changement in passage.changements or ("configuration inchangée",):
        print(f"  {changement}")


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--dossier", required=True)
    parseur.add_argument("--executer", action="store_true", help="écrit en base")
    parseur.add_argument(
        "--y-compris-demo",
        action="store_true",
        help="autorise le portefeuille de démo (le menu Démo ne sait pas l'annuler)",
    )
    args = parseur.parse_args()

    engine = engine_depuis_env()
    depot = PostgresDossierRepository(engine)
    dossier = depot.obtenir(DossierId(args.dossier))
    if dossier is None:
        print(f"Dossier inconnu : {args.dossier}", file=sys.stderr)
        return 1
    if args.executer and dossier.tenant_id == TENANT_DEMO and not args.y_compris_demo:
        print(
            "Portefeuille de démo : les écritures d'à-nouveaux sont verrouillées et le menu Démo "
            "ne les efface pas. Relancer avec --y-compris-demo pour le faire quand même.",
            file=sys.stderr,
        )
        return 1
    ledger = PostgresLedgerService(engine)
    maintenant = datetime.now(UTC).replace(tzinfo=None)
    try:
        passage = preparer_passage(
            dossier,
            ledger,
            PostgresDecisionRepository(engine),
            PostgresAvenantRegimeRepository(engine).lister(dossier.id),
            maintenant.date(),
        )
    except PassageRefuse as exc:
        print(f"{dossier.id} : passage refusé, {exc}", file=sys.stderr)
        return 1
    _afficher(passage)
    if not args.executer:
        print("Simulation : rien n'est écrit (--executer pour clore).")
        return 0
    executer_passage(
        passage, ledger, depot, PostgresExerciceRepository(engine), maintenant, "ligne_de_commande"
    )
    print("Exercice clos, nouvel exercice ouvert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
