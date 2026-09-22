"""Synchronisation d'un dossier réel : lot du fournisseur -> archive brute ->
catégorisation -> écritures (doc 12 §1.2, doc 16 §9).

Ce que ça garantit, et qui n'était pas vrai du chemin de démo :

- **Idempotent.** L'id d'une écriture dérive de l'id de transaction du
  fournisseur (`{dossier}:{source}-{id}`), jamais d'un compteur : relancer la
  synchro, ou relire une fenêtre qui se recouvre, ne crée aucun doublon.
- **Reprise sûre.** Ordre : archive brute, proposition, écriture, puis
  curseur en dernier. Une interruption au milieu se rattrape au passage
  suivant ; au pire une proposition orpheline, sans effet.
- **Le ledger reste append-only** (doc 06 §1). Une transaction modifiée ou
  supprimée côté banque *après* avoir été comptabilisée n'est ni réécrite ni
  ignorée : elle part en quarantaine pour décision humaine (contre-passation
  à construire).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from axelcompta.categorize.models import Etage, ProposedEntry
from axelcompta.categorize.pipeline import CategorizationPipeline
from axelcompta.core.ids import EcritureId
from axelcompta.ingestion.journal import JournalIngestion
from axelcompta.ingestion.providers.base import LotTransactions
from axelcompta.ledger.models import Ecriture, Sens
from axelcompta.ledger.service import LedgerService
from axelcompta.tenants.models import Dossier

from .auto_accept import construire_ecriture_categorisee
from .propositions import PropositionRepository

COMPTE_ATTENTE = "471"

# Sans settlement plateforme réconcilié (Rollee, doc 13 §4), un virement Uber
# ou Bolt ne peut pas être comptabilisé en 706 : la ventilation TVA vient du
# relevé de la plateforme, pas de la banque. En attente, jamais en produit.
CATEGORIES_EN_ATTENTE_DE_SETTLEMENT = frozenset({"recettes_plateformes", "commissions_plateformes"})

# Seuils PROVISOIRES d'acceptation automatique. Les probabilités du modèle ne
# sont pas calibrées (ADR-007) et sa précision n'est mesurée que contre le
# mapping (79,5 %), donc le seuil ML est volontairement haut. Tout ce qui est
# en dessous va au compte d'attente, donc dans la file de revue de l'indiv.
SEUIL_REGLE = 0.75
SEUIL_ML = 0.90


class SourceTransactions(Protocol):
    async def lire_lot(self, dossier: Dossier, depuis_maj: datetime | None) -> LotTransactions: ...


@dataclass(frozen=True, slots=True)
class RapportSynchro:
    nouvelles: int
    a_trancher: int  # parmi les nouvelles, celles envoyées au compte d'attente
    deja_connues: int
    modifiees_signalees: int
    supprimees_signalees: int
    rejets: int
    curseur: datetime | None


def choisir_compte(proposition: ProposedEntry, comptes: dict[str, str]) -> str:
    """Compte d'imputation, ou 471 quand la proposition ne mérite pas de
    confiance sans regard humain."""
    if proposition.categorie in CATEGORIES_EN_ATTENTE_DE_SETTLEMENT:
        return COMPTE_ATTENTE
    seuil = SEUIL_REGLE if proposition.etage is Etage.REGLE else SEUIL_ML
    if proposition.etage not in (Etage.REGLE, Etage.ML) or proposition.confiance < seuil:
        return COMPTE_ATTENTE
    return comptes.get(proposition.categorie, COMPTE_ATTENTE)


def _signature(ecriture: Ecriture) -> tuple[int, object]:
    """(montant signé côté banque, date) : ce qui ne doit plus bouger une fois
    comptabilisé."""
    for ligne in ecriture.lignes:
        if ligne.compte == "512":
            signe = 1 if ligne.sens is Sens.DEBIT else -1
            return signe * ligne.montant.centimes, ecriture.date
    return 0, ecriture.date


def _id_ecriture(dossier: Dossier, source_nom: str, transaction_id: str) -> EcritureId:
    return EcritureId(f"{dossier.id}:{source_nom}-{transaction_id}")


def _archiver_lot(
    dossier: Dossier, source_nom: str, journal: JournalIngestion, lot: LotTransactions
) -> None:
    for brute in lot.brutes:
        journal.archiver(
            dossier.id,
            source_nom,
            _texte_ou_none(brute.get("id")),
            _texte_ou_none(brute.get("updated_at")),
            brute,
        )
    for rejet in lot.rejets:
        journal.mettre_en_quarantaine(
            dossier.id, source_nom, f"ligne_illisible : {rejet.raison}", None, rejet.payload
        )


@dataclass(slots=True)
class _Compteurs:
    nouvelles: int = 0
    a_trancher: int = 0
    connues: int = 0
    modifiees: int = 0
    supprimees: int = 0


def _traiter_transactions(
    dossier: Dossier,
    source_nom: str,
    lot: LotTransactions,
    comptabilisees: dict[EcritureId, Ecriture],
    journal: JournalIngestion,
    ledger: LedgerService,
    propositions: PropositionRepository,
    pipeline: CategorizationPipeline,
    comptes: dict[str, str],
) -> _Compteurs:
    compteurs = _Compteurs()
    for transaction in lot.transactions:
        ecriture_id = _id_ecriture(dossier, source_nom, transaction.id)
        existante = comptabilisees.get(ecriture_id)
        if existante is not None:
            if _signature(existante) == (transaction.montant_cts, transaction.date):
                compteurs.connues += 1
            else:
                compteurs.modifiees += 1
                journal.mettre_en_quarantaine(
                    dossier.id,
                    source_nom,
                    "modifiee_apres_comptabilisation",
                    transaction.id,
                    transaction.raw_payload,
                )
            continue
        proposition = pipeline.categoriser(dossier.id, transaction)
        compte = choisir_compte(proposition, comptes)
        ecriture = dataclasses.replace(
            construire_ecriture_categorisee(transaction, proposition, compte, 0), id=ecriture_id
        )
        propositions.enregistrer(ecriture_id, proposition)
        ledger.enregistrer(ecriture)
        compteurs.nouvelles += 1
        compteurs.a_trancher += compte == COMPTE_ATTENTE
    return compteurs


def _signaler_supprimees(
    dossier: Dossier,
    source_nom: str,
    lot: LotTransactions,
    comptabilisees: dict[EcritureId, Ecriture],
    journal: JournalIngestion,
) -> int:
    signalees = 0
    for transaction_id in lot.supprimees:
        if _id_ecriture(dossier, source_nom, transaction_id) in comptabilisees:
            signalees += 1
            journal.mettre_en_quarantaine(
                dossier.id,
                source_nom,
                "supprimee_apres_comptabilisation",
                transaction_id,
                {"id": transaction_id},
            )
    return signalees


async def synchroniser_dossier(
    dossier: Dossier,
    source: SourceTransactions,
    source_nom: str,
    journal: JournalIngestion,
    ledger: LedgerService,
    propositions: PropositionRepository,
    pipeline: CategorizationPipeline,
    comptes_par_categorie: dict[str, str],
) -> RapportSynchro:
    lot = await source.lire_lot(dossier, journal.curseur(dossier.id, source_nom))
    _archiver_lot(dossier, source_nom, journal, lot)
    comptabilisees = {e.id: e for e in ledger.grand_livre(dossier.id)}
    compteurs = _traiter_transactions(
        dossier,
        source_nom,
        lot,
        comptabilisees,
        journal,
        ledger,
        propositions,
        pipeline,
        comptes_par_categorie,
    )
    supprimees = _signaler_supprimees(dossier, source_nom, lot, comptabilisees, journal)
    # Curseur en dernier : une interruption plus haut se rattrape au prochain passage.
    if lot.curseur is not None:
        journal.avancer_curseur(dossier.id, source_nom, lot.curseur)
    return RapportSynchro(
        nouvelles=compteurs.nouvelles,
        a_trancher=compteurs.a_trancher,
        deja_connues=compteurs.connues,
        modifiees_signalees=compteurs.modifiees,
        supprimees_signalees=supprimees,
        rejets=len(lot.rejets),
        curseur=lot.curseur,
    )


def _texte_ou_none(valeur: object) -> str | None:
    return None if valeur is None else str(valeur)
