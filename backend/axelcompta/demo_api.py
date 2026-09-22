"""API FastAPI dédiée à la démo produit (doc 17 §9, doc 19) — sert les 3
chauffeurs type au frontend Next.js.

Distincte de `axelcompta.api` (la vraie API produit, doc 03 §7, encore un
squelette sans route) : ceci est une composition root comme
`demo_chauffeurs_type.py` (doc 18), pas soumise aux mêmes contraintes de
dépendance qu'un module métier — elle peut importer n'importe quoi
directement, y compris une autre composition root.

**Bloc A/C (doc 17 §9) : la file de revue est maintenant réelle.**
`POST /dossiers/{id}/transactions/{ecriture_id}/decision` accepte/reclasse
une écriture « à trancher » — la décision est persistée pour de vrai
(`workflow.decisions_postgres`, doc 17 §9 bloc A), pas juste un changement
d'état côté React. Requiert donc `DATABASE_URL` et un Postgres démarré
(`docker compose up -d db` puis `alembic upgrade head` depuis `backend/`)
— **changement par rapport à avant** : la démo n'était jusqu'ici pas
censée avoir besoin d'infra pour tourner.

**Depuis le 2026-09-21, tout est lu en Postgres** : dossiers et tenants
(`tenants/`), ledger (`PostgresLedgerService`), propositions d'origine du
pipeline (`workflow/propositions*`). Rien n'est recalculé à la volée. Les
décisions humaines restent une couche append-only réappliquée par-dessus le
ledger persisté (`_ledger_avec_decisions`). `python -m axelcompta.demo_seed`
amorce la base avec les 3 profils de démo ; le portefeuille visible d'un
gestionnaire est celui de son `tenant_id` (jeton), pas une constante.

Usage : `uvicorn axelcompta.demo_api:app --reload --port 8000` depuis
backend/ (nécessite `pip install -e ".[dev]"` pour uvicorn).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.closing.models import LiassePivot
from axelcompta.core.db import engine_depuis_env
from axelcompta.core.ids import DossierId, EcritureId, TenantId, UserId
from axelcompta.demo_auth import IdentiteAuthentifiee, identite_chauffeur_optionnelle
from axelcompta.demo_comptes import (
    CompteDejaInviteError,
    CompteRepository,
    StatutInvitation,
    SupabaseCompteRepository,
    SupabaseConfig,
)
from axelcompta.demo_justificatifs import (
    FichierJustificatifRepository,
    JustificatifRepository,
)
from axelcompta.filings.cerfa_2065 import PdfCerfa2065Renderer
from axelcompta.filings.export_comptable import exporter_balance, exporter_grand_livre
from axelcompta.filings.fec import exporter_fec
from axelcompta.filings.inpi_depot import PdfDepotInpiRenderer
from axelcompta.filings.liasse_simplifiee import PdfLiasseSimplifieeRenderer
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Sens
from axelcompta.ledger.repository import PostgresLedgerService
from axelcompta.ledger.service import LedgerService
from axelcompta.packs.vtc_demo import charger_compte_par_categorie
from axelcompta.tenants.models import Dossier
from axelcompta.tenants.postgres import PostgresDossierRepository
from axelcompta.tenants.repository import DossierRepository
from axelcompta.workflow.decisions import DecisionHumaine, DecisionRepository
from axelcompta.workflow.decisions_postgres import PostgresDecisionRepository
from axelcompta.workflow.propositions import PropositionRepository
from axelcompta.workflow.propositions_postgres import PostgresPropositionRepository
from axelcompta.workflow.revue import CategorieInconnueError, resoudre_ecriture_a_trancher
from axelcompta.workflow.signature import SignatureRepository
from axelcompta.workflow.signature_demo import SignatureDemoProvider
from axelcompta.workflow.signature_memory import InMemorySignatureRepository

# doc 17 §9 Semaine 3 : racine de stockage des justificatifs de démo — pas
# le stockage WORM réel (V1, doc 04 §1), juste de quoi prouver que la photo
# s'attache vraiment à la transaction.
RACINE_JUSTIFICATIFS_DEMO = (
    Path(__file__).resolve().parent.parent / "_demo_output" / "justificatifs"
)
_TYPES_IMAGE_ACCEPTES = ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif")

COMPTE_ATTENTE = "471"  # doc 06 §2 : compte d'attente par défaut, "à trancher"
TYPE_DOCUMENT_GREFFE_INPI = "greffe_inpi"  # doc 20 : dépôt des comptes annuels
ORIGINE_FRONTEND_DEV = "http://localhost:3000"
# **Retiré le 2026-09-11 (doc 19 §8bis)** : `UTILISATEUR_DEMO` (stub pour
# le cas « gestionnaire sans login » sur les routes de tranchage/signature)
# n'a plus de raison d'être — ces routes exigent désormais un vrai jeton
# indiv (`_verifier_acces_dossier`), la révision structurante du même jour
# ayant retiré au gestionnaire tout accès à ces actions (doc 19 §2.1/§2.4).


class DossierResume(BaseModel):
    dossier_id: str
    nom: str
    tva_recettes_regime: str
    plateformes: list[str]
    exercice_debut: str | None
    exercice_fin: str | None
    ca_ht_cts: int
    charges_cts: int
    resultat_cts: int
    tresorerie_cts: int
    tva_a_payer_cts: int
    nb_transactions: int
    nb_a_trancher: int
    statut_invitation: str | None  # None = "non_invité" (doc 19 §3.2) ; sinon "invité" | "actif"
    mode_acces_bancaire: str  # "gestionnaire" | "chauffeur_direct" (doc 19 §4)
    greffe_inpi_signe: (
        bool  # doc 20 : dossier de dépôt des comptes annuels signé (démo, pas qualifié)
    )


class DossierAgregat(BaseModel):
    """Ce que le gestionnaire voit d'un dossier (doc 19 §2.1) : agrégats et
    onboarding, rien de dérivé du détail (doc 19 §2.4). Volontairement un
    modèle distinct de `DossierResume` plutôt qu'un filtre a posteriori : un
    champ ajouté plus tard à `DossierResume` ne fuit pas vers le gestionnaire
    par inadvertance."""

    dossier_id: str
    nom: str
    tva_recettes_regime: str
    plateformes: list[str]
    exercice_debut: str | None
    exercice_fin: str | None
    ca_ht_cts: int
    charges_cts: int
    resultat_cts: int
    statut_invitation: str | None
    mode_acces_bancaire: str


class TransactionVue(BaseModel):
    ecriture_id: str
    date: str
    libelle: str
    montant_cts: int  # signé : positif = argent reçu, négatif = argent sorti (ligne 512)
    compte: str
    statut: str  # "validé" | "à trancher" — vocabulaire unique de badge (doc 11 §4)
    a_justificatif: bool  # doc 17 §9 Semaine 3 : une photo a été jointe (contenu non lu)


class DecisionEntree(BaseModel):
    categorie: str  # "usage_personnel" ou toute catégorie du pack (doc 17 §9 bloc C)


class InvitationEntree(BaseModel):
    email: str  # doc 17 §9 bloc B — pas les 3 profils démo, un vrai e-mail entré à la volée


MAX_INVITATIONS_PAR_LOT = 500
_FORME_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LigneInvitationEntree(BaseModel):
    dossier_id: str
    email: str


class InvitationsMasseEntree(BaseModel):
    invitations: list[LigneInvitationEntree] = Field(max_length=MAX_INVITATIONS_PAR_LOT)


class LigneInvitationVue(BaseModel):
    dossier_id: str
    email: str
    # invité | deja_invite | dossier_inconnu | email_invalide | doublon_dans_le_lot | erreur
    resultat: str


class InvitationsMasseVue(BaseModel):
    lignes: list[LigneInvitationVue]
    nb_invitees: int


class InvitationVue(BaseModel):
    dossier_id: str
    email: str
    statut: str  # "invité" | "actif" — jamais "non_invité" ici, ça n'existe qu'en absence


class SignatureGreffeVue(BaseModel):
    dossier_id: str
    signe: bool
    signe_le: str
    qualifie: bool  # doc 20 §4 : toujours False en démo, jamais une vraie signature RGS


def _ledger_avec_decisions(
    dossier: Dossier, base: LedgerService, decisions: DecisionRepository
) -> InMemoryLedgerService:
    """Le ledger persisté, avec les décisions humaines ré-appliquées par-dessus
    (doc 17 §9 bloc A/C). Les écritures d'origine ne sont jamais modifiées en
    base (append-only, doc 06 §1) : une décision est une couche séparée."""
    ecritures = base.grand_livre(dossier.id)
    dernieres_decisions = {
        decision.ecriture_id: decision for decision in decisions.lister_decisions(dossier.id)
    }
    comptes = charger_compte_par_categorie()
    resultat = InMemoryLedgerService()
    for ecriture in ecritures:
        decision = dernieres_decisions.get(ecriture.id)
        if decision is not None:
            ecriture = resoudre_ecriture_a_trancher(
                ecriture, decision.categorie, dossier.forme_juridique, comptes
            )
        resultat.enregistrer(ecriture)
    return resultat


def _statut_invitation_vue(statut: StatutInvitation) -> str:
    return {StatutInvitation.INVITE: "invité", StatutInvitation.ACTIF: "actif"}[statut]


def _construire_liasse(dossier: Dossier, ledger: InMemoryLedgerService) -> LiassePivot:
    """Semaine 4 (doc 17 §9) : même appel que `_resume` (clôture) et que les
    exports de `demo_chauffeurs_type._executer_un_chauffeur`, mais sur le
    ledger **avec les décisions humaines déjà appliquées**
    (`_ledger_avec_decisions`) : une transaction tranchée en 455/108 doit
    sortir de la liasse téléchargée, pas seulement du dashboard."""
    return ClotureSimplifieeService(ledger).cloturer(
        dossier.id, exercice=str(dossier.exercice_debut.year)
    )


def _resume(
    dossier: Dossier,
    ledger: InMemoryLedgerService,
    comptes: CompteRepository,
    signatures: SignatureRepository,
) -> DossierResume:
    ecritures = ledger.grand_livre(dossier.id)
    liasse = _construire_liasse(dossier, ledger)
    nb_a_trancher = sum(
        1 for e in ecritures if any(ligne.compte == COMPTE_ATTENTE for ligne in e.lignes)
    )
    invitation = comptes.statut(dossier.id)
    document_greffe = signatures.dernier(dossier.id, TYPE_DOCUMENT_GREFFE_INPI)
    return DossierResume(
        dossier_id=dossier.id,
        nom=dossier.nom,
        tva_recettes_regime=dossier.tva_recettes_regime,
        plateformes=list(dossier.plateformes),
        exercice_debut=liasse.exercice_debut.isoformat() if liasse.exercice_debut else None,
        exercice_fin=liasse.exercice_fin.isoformat() if liasse.exercice_fin else None,
        ca_ht_cts=liasse.cases.get("CA_HT", 0),
        charges_cts=liasse.cases.get("CHARGES", 0),
        resultat_cts=liasse.cases.get("RESULTAT", 0),
        tresorerie_cts=liasse.cases.get("TRESORERIE", 0),
        tva_a_payer_cts=liasse.cases.get("TVA_A_PAYER", 0),
        nb_transactions=len(ecritures),
        nb_a_trancher=nb_a_trancher,
        statut_invitation=_statut_invitation_vue(invitation.statut) if invitation else None,
        mode_acces_bancaire=dossier.mode_acces_bancaire,
        greffe_inpi_signe=document_greffe is not None,
    )


def _verifier_acces_dossier(
    dossier_id: str, identite: IdentiteAuthentifiee | None
) -> IdentiteAuthentifiee:
    """doc 19 §8bis (2026-09-11) : toutes les routes de niveau dossier sont
    indiv-exclusives depuis la révision structurante du même jour (doc 19
    §2.1/§2.4) — un jeton valide est désormais **obligatoire**, pas
    seulement cohérent s'il est fourni. Avant : l'absence de jeton
    (cas gestionnaire, jamais de login) passait sans restriction ; ce
    chemin n'a plus de raison d'être, rien dans l'app n'appelle plus ces
    routes sans jeton. Retourne l'identité (narrowée, non optionnelle) pour
    que l'appelant n'ait plus besoin du stub `UTILISATEUR_DEMO`."""
    if identite is None:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    if identite.dossier_id != dossier_id:
        raise HTTPException(status_code=403, detail="Ce dossier ne vous appartient pas.")
    return identite


def _verifier_acces_gestionnaire(identite: IdentiteAuthentifiee | None) -> TenantId:
    """doc 03 §7 : le lien `tenant_id` ouvre le portefeuille (agrégats,
    invitations), jamais le détail d'un dossier — voir
    `_verifier_acces_dossier`, qui ne regarde que `dossier_id`. Un compte
    indiv seul n'a pas de `tenant_id` : 403. Retourne le tenant de l'appelant
    (les dossiers visibles sont ensuite filtrés par ce tenant)."""
    if identite is None:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    if identite.tenant_id is None:
        raise HTTPException(status_code=403, detail="Compte sans portefeuille.")
    return identite.tenant_id


def _agregat(resume: DossierResume) -> DossierAgregat:
    return DossierAgregat(
        dossier_id=resume.dossier_id,
        nom=resume.nom,
        tva_recettes_regime=resume.tva_recettes_regime,
        plateformes=resume.plateformes,
        exercice_debut=resume.exercice_debut,
        exercice_fin=resume.exercice_fin,
        ca_ht_cts=resume.ca_ht_cts,
        charges_cts=resume.charges_cts,
        resultat_cts=resume.resultat_cts,
        statut_invitation=resume.statut_invitation,
        mode_acces_bancaire=resume.mode_acces_bancaire,
    )


def _transactions_dossier(
    dossier: Dossier, ledger: InMemoryLedgerService, justificatifs: JustificatifRepository
) -> list[TransactionVue]:
    """Extrait de la route (doc 08 §2 : longueur de fonction)."""
    return [
        _transaction_vue(e, justificatifs.a_un_justificatif(dossier.id, e.id))
        for e in ledger.grand_livre(dossier.id)
    ]


def _montant_512(ecriture: Ecriture) -> int:
    """Le sens de la ligne 512 donne le montant signé façon relevé bancaire
    (doc 11 §1 : « chiffres irréprochables »), pas le montant absolu."""
    for ligne in ecriture.lignes:
        if ligne.compte == "512":
            signe = 1 if ligne.sens is Sens.DEBIT else -1
            return signe * ligne.montant.centimes
    return 0


def _compte_affiche(ecriture: Ecriture) -> str:
    """Une écriture de settlement a plusieurs comptes en contrepartie du 512
    (706/622/44566/44571) — pas un seul compte à afficher tel quel."""
    autres = [ligne.compte for ligne in ecriture.lignes if ligne.compte != "512"]
    return autres[0] if len(autres) == 1 else "règlement plateforme"


def _transaction_vue(ecriture: Ecriture, a_justificatif: bool) -> TransactionVue:
    a_trancher = any(ligne.compte == COMPTE_ATTENTE for ligne in ecriture.lignes)
    return TransactionVue(
        ecriture_id=ecriture.id,
        date=ecriture.date.isoformat(),
        libelle=ecriture.libelle,
        montant_cts=_montant_512(ecriture),
        compte=_compte_affiche(ecriture),
        statut="à trancher" if a_trancher else "validé",
        a_justificatif=a_justificatif,
    )


_ENGINE_DEMO: Engine | None = None


def _engine() -> Engine:
    """Engine Postgres partagé, construit **à la première requête réelle**,
    pas à l'import du module : importer `demo_api` (pour ses tests, par
    exemple) ne doit pas exiger `DATABASE_URL`. Les tests surchargent les
    dépendances ci-dessous (`app.dependency_overrides[...] = ...`) avec des
    implémentations en mémoire pour ne jamais l'appeler du tout."""
    global _ENGINE_DEMO
    if _ENGINE_DEMO is None:
        _ENGINE_DEMO = engine_depuis_env()
    return _ENGINE_DEMO


def get_decisions() -> DecisionRepository:
    """Dépendance FastAPI — voir `_engine`."""
    return PostgresDecisionRepository(_engine())


def get_dossiers() -> DossierRepository:
    """Dépendance FastAPI — dossiers et tenants (`tenants/`), peuplés par
    `python -m axelcompta.demo_seed` (voir backend/README.md)."""
    return PostgresDossierRepository(_engine())


def get_ledger() -> LedgerService:
    """Dépendance FastAPI — le ledger persisté (écritures d'origine, sans les
    décisions humaines, qui sont une couche séparée)."""
    return PostgresLedgerService(_engine())


def get_propositions() -> PropositionRepository:
    """Dépendance FastAPI — ce que le pipeline avait proposé par écriture."""
    return PostgresPropositionRepository(_engine())


DecisionsDep = Annotated[DecisionRepository, Depends(get_decisions)]
DossiersDep = Annotated[DossierRepository, Depends(get_dossiers)]
LedgerBaseDep = Annotated[LedgerService, Depends(get_ledger)]
PropositionsDep = Annotated[PropositionRepository, Depends(get_propositions)]


_CLIENT_COMPTES: SupabaseCompteRepository | None = None


def get_comptes() -> CompteRepository:
    """Dépendance FastAPI — même idiome que `get_decisions` : le client
    Supabase se construit à la première requête réelle, jamais à l'import
    (`SupabaseConfig.depuis_env()` échouerait sinon sans
    SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY). Les tests surchargent avec
    `InMemoryCompteRepository` (doc 17 §9 bloc B — Louis, 2026-09-07 :
    « je ne veux pas dépendre de Supabase pour tous les tests »)."""
    global _CLIENT_COMPTES
    if _CLIENT_COMPTES is None:
        _CLIENT_COMPTES = SupabaseCompteRepository(SupabaseConfig.depuis_env())
    return _CLIENT_COMPTES


ComptesDep = Annotated[CompteRepository, Depends(get_comptes)]

IdentiteDep = Annotated[IdentiteAuthentifiee | None, Depends(identite_chauffeur_optionnelle)]


def get_dossier_autorise(dossier_id: str, identite: IdentiteDep, dossiers: DossiersDep) -> Dossier:
    """Accès indiv à un dossier. L'ordre compte : identité (401), droit sur
    ce dossier (403), **puis** existence (404). Inverser laisserait un appelant
    non autorisé distinguer un dossier inexistant d'un dossier interdit."""
    _verifier_acces_dossier(dossier_id, identite)
    dossier = dossiers.obtenir(DossierId(dossier_id))
    if dossier is None:
        raise HTTPException(status_code=404, detail=f"Dossier inconnu : {dossier_id}")
    return dossier


DossierDep = Annotated[Dossier, Depends(get_dossier_autorise)]


def get_dossier_du_portefeuille(
    dossier_id: str, identite: IdentiteDep, dossiers: DossiersDep
) -> Dossier:
    """Accès gestionnaire à un dossier **de son portefeuille**. Un dossier
    d'un autre tenant répond 404, pas 403 : un gestionnaire ne doit pas
    pouvoir sonder l'existence des dossiers d'un autre portefeuille."""
    tenant_id = _verifier_acces_gestionnaire(identite)
    dossier = dossiers.obtenir(DossierId(dossier_id))
    if dossier is None or dossier.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=f"Dossier inconnu : {dossier_id}")
    return dossier


DossierPortefeuilleDep = Annotated[Dossier, Depends(get_dossier_du_portefeuille)]


def get_ledger_du_dossier(
    dossier: DossierDep, base: LedgerBaseDep, decisions: DecisionsDep
) -> InMemoryLedgerService:
    return _ledger_avec_decisions(dossier, base, decisions)


LedgerDossierDep = Annotated[InMemoryLedgerService, Depends(get_ledger_du_dossier)]


_REPO_JUSTIFICATIFS: FichierJustificatifRepository | None = None


def get_justificatifs() -> JustificatifRepository:
    """Dépendance FastAPI — même idiome que `get_decisions`/`get_comptes` :
    construite à la première requête réelle. Les tests surchargent avec
    `InMemoryJustificatifRepository` (jamais de fichier réel écrit)."""
    global _REPO_JUSTIFICATIFS
    if _REPO_JUSTIFICATIFS is None:
        _REPO_JUSTIFICATIFS = FichierJustificatifRepository(RACINE_JUSTIFICATIFS_DEMO)
    return _REPO_JUSTIFICATIFS


JustificatifsDep = Annotated[JustificatifRepository, Depends(get_justificatifs)]


_SIGNATURES_INPI = InMemorySignatureRepository()


def get_signatures_inpi() -> SignatureRepository:
    """Dépendance FastAPI — en mémoire seulement, contrairement à
    `get_decisions` (doc 20 : pas de vraie signature qualifiée possible en
    démo de toute façon, la persistance Postgres n'apporterait rien
    aujourd'hui ; graduera vers une vraie persistance le jour où le
    prestataire réel — ADR-004 — sera branché). Instance de niveau module
    directement (pas de connexion externe à retarder comme pour
    Postgres/Supabase). Les tests surchargent avec une instance fraîche
    pour s'isoler les uns des autres."""
    return _SIGNATURES_INPI


SignaturesInpiDep = Annotated[SignatureRepository, Depends(get_signatures_inpi)]


def _trancher(
    dossier: Dossier,
    ecriture_id: str,
    categorie: str,
    base: LedgerService,
    decisions: DecisionRepository,
    propositions: PropositionRepository,
    decide_par: UserId,
) -> Ecriture:
    """doc 17 §9 bloc C : la décision humaine, pour de vrai — déclenche le
    `workflow` testé (doc 05 §5), pas un changement d'état côté React seul.
    Extrait de la route (doc 08 §2 : longueur de fonction) plutôt que fait
    inline. `decide_par` est toujours l'identité réelle de l'indiv depuis le
    2026-09-11 (doc 19 §8bis)."""
    ecriture = next((e for e in base.grand_livre(dossier.id) if e.id == ecriture_id), None)
    if ecriture is None:
        raise HTTPException(status_code=404, detail=f"Écriture inconnue : {ecriture_id}")
    if decisions.decision_courante(dossier.id, EcritureId(ecriture_id)) is not None:
        raise HTTPException(
            status_code=409,
            detail="Cette écriture a déjà été tranchée (doc 05 §5 : décision immuable).",
        )
    if not any(ligne.compte == COMPTE_ATTENTE for ligne in ecriture.lignes):
        raise HTTPException(status_code=409, detail="Cette écriture n'est pas à trancher.")
    proposition = propositions.obtenir(dossier.id, EcritureId(ecriture_id))
    if proposition is None:
        raise HTTPException(
            status_code=500,
            detail="Aucune proposition d'origine pour cette écriture (incohérence interne).",
        )
    comptes = charger_compte_par_categorie()
    try:
        resoudre_ecriture_a_trancher(ecriture, categorie, dossier.forme_juridique, comptes)
    except CategorieInconnueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    decisions.enregistrer_decision(
        DecisionHumaine(
            dossier_id=dossier.id,
            ecriture_id=EcritureId(ecriture_id),
            categorie=categorie,
            etage_origine=proposition.etage,
            confiance_origine=proposition.confiance,
            decide_par=decide_par,
            decide_le=datetime.now(UTC),
        )
    )
    ledger_a_jour = _ledger_avec_decisions(dossier, base, decisions)
    return next(e for e in ledger_a_jour.grand_livre(dossier.id) if e.id == ecriture_id)


def _joindre_justificatif(
    dossier: Dossier,
    ecriture_id: str,
    fichier: UploadFile,
    ledger: InMemoryLedgerService,
    justificatifs: JustificatifRepository,
) -> Ecriture:
    """doc 17 §9 Semaine 3, doc 19 §5.7 : « photo de justificatif au fil de
    l'eau, associée automatiquement à la transaction » — le contenu n'est
    jamais lu (pas d'OCR, doc 17 §8). Extrait de la route (doc 08 §2),
    même logique que `_trancher`.

    Lecture synchrone (`fichier.file.read()`, pas `await fichier.read()`) :
    `fichier.file` est un objet fichier synchrone standard
    (`SpooledTemporaryFile`), pas une coroutine — lecture bloquante, mais un
    JPEG de démo tient en mémoire sans souci."""
    ecriture = next((e for e in ledger.grand_livre(dossier.id) if e.id == ecriture_id), None)
    if ecriture is None:
        raise HTTPException(status_code=404, detail=f"Écriture inconnue : {ecriture_id}")
    if fichier.content_type not in _TYPES_IMAGE_ACCEPTES:
        raise HTTPException(
            status_code=400, detail="Seules les photos sont acceptées (jpeg/png/webp/heic)."
        )
    contenu = fichier.file.read()
    extension = Path(fichier.filename or "").suffix or ".jpg"
    justificatifs.enregistrer(dossier.id, ecriture_id, contenu, extension)
    return ecriture


def _configurer_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGINE_FRONTEND_DEV],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


def _enregistrer_routes_dossiers(app: FastAPI) -> None:
    @app.get("/dossiers", response_model=list[DossierAgregat])
    def lister_dossiers(
        dossiers: DossiersDep,
        base: LedgerBaseDep,
        decisions: DecisionsDep,
        comptes: ComptesDep,
        signatures: SignaturesInpiDep,
        identite: IdentiteDep,
    ) -> list[DossierAgregat]:
        """Vue gestionnaire (doc 19 §2.1) : agrégats des dossiers **de son
        portefeuille** seulement (`tenant_id` du jeton), rien d'autre."""
        tenant_id = _verifier_acces_gestionnaire(identite)
        return [
            _agregat(_resume(d, _ledger_avec_decisions(d, base, decisions), comptes, signatures))
            for d in dossiers.lister_par_tenant(tenant_id)
        ]

    @app.get("/dossiers/{dossier_id}", response_model=DossierResume)
    def obtenir_dossier(
        dossier: DossierDep,
        ledger: LedgerDossierDep,
        comptes: ComptesDep,
        signatures: SignaturesInpiDep,
    ) -> DossierResume:
        return _resume(dossier, ledger, comptes, signatures)


def _enregistrer_routes_transactions(app: FastAPI) -> None:
    @app.get("/dossiers/{dossier_id}/transactions", response_model=list[TransactionVue])
    def lister_transactions(
        dossier: DossierDep, ledger: LedgerDossierDep, justificatifs: JustificatifsDep
    ) -> list[TransactionVue]:
        return _transactions_dossier(dossier, ledger, justificatifs)

    @app.post(
        "/dossiers/{dossier_id}/transactions/{ecriture_id}/decision",
        response_model=TransactionVue,
    )
    def trancher_transaction(
        ecriture_id: str,
        entree: DecisionEntree,
        dossier: DossierDep,
        base: LedgerBaseDep,
        decisions: DecisionsDep,
        propositions: PropositionsDep,
        justificatifs: JustificatifsDep,
        identite: IdentiteDep,
    ) -> TransactionVue:
        """Indiv qui tranche sa propre écriture (doc 19 §5.6, doc 19 §8bis :
        jeton obligatoire depuis le 2026-09-11) — `DossierDep` refuse déjà
        l'accès à un autre dossier."""
        identite = _verifier_acces_dossier(dossier.id, identite)
        ecriture = _trancher(
            dossier, ecriture_id, entree.categorie, base, decisions, propositions, identite.user_id
        )
        return _transaction_vue(ecriture, justificatifs.a_un_justificatif(dossier.id, ecriture_id))

    @app.post(
        "/dossiers/{dossier_id}/transactions/{ecriture_id}/justificatif",
        response_model=TransactionVue,
    )
    def joindre_justificatif(
        ecriture_id: str,
        fichier: UploadFile,
        dossier: DossierDep,
        ledger: LedgerDossierDep,
        justificatifs: JustificatifsDep,
    ) -> TransactionVue:
        """Justificatif d'une transaction de **son propre dossier** (doc 19
        §5.7) : `DossierDep` refuse tout autre accès, gestionnaire compris."""
        ecriture = _joindre_justificatif(dossier, ecriture_id, fichier, ledger, justificatifs)
        return _transaction_vue(ecriture, justificatifs.a_un_justificatif(dossier.id, ecriture_id))


def _enregistrer_routes_invitation(app: FastAPI) -> None:
    @app.post("/invitations/en-masse", response_model=InvitationsMasseVue)
    def inviter_en_masse(
        entree: InvitationsMasseEntree,
        dossiers: DossiersDep,
        comptes: ComptesDep,
        identite: IdentiteDep,
    ) -> InvitationsMasseVue:
        """doc 19 §3.1 : le gestionnaire invite ses chauffeurs depuis une base
        clients, pas seulement un par un. Jusqu'à `MAX_INVITATIONS_PAR_LOT`
        lignes, résultat ligne par ligne."""
        tenant_id = _verifier_acces_gestionnaire(identite)
        du_portefeuille = {str(d.id) for d in dossiers.lister_par_tenant(tenant_id)}
        return _inviter_en_masse(entree.invitations, du_portefeuille, comptes)

    @app.post("/dossiers/{dossier_id}/inviter", response_model=InvitationVue)
    def inviter_chauffeur(
        entree: InvitationEntree, dossier: DossierPortefeuilleDep, comptes: ComptesDep
    ) -> InvitationVue:
        """doc 17 §9 bloc B, doc 19 §3.1 : le gestionnaire invite, jamais
        de self-signup (disable_signup, vérifié 2026-09-07). Envoie un
        vrai e-mail via Supabase Auth — pas un simulateur. Uniquement pour un
        dossier de son propre portefeuille (`DossierPortefeuilleDep`)."""
        try:
            invitation = comptes.inviter(dossier.id, entree.email)
        except CompteDejaInviteError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return InvitationVue(
            dossier_id=invitation.dossier_id,
            email=invitation.email,
            statut=_statut_invitation_vue(invitation.statut),
        )


def _inviter_en_masse(
    lignes: list[LigneInvitationEntree],
    dossiers_du_portefeuille: set[str],
    comptes: CompteRepository,
) -> InvitationsMasseVue:
    """Traite chaque ligne indépendamment : une ligne en échec n'empêche pas
    les autres (un fichier de 200 chauffeurs ne doit pas échouer en bloc sur
    une adresse mal saisie). Un dossier hors du portefeuille est déclaré
    « inconnu », comme s'il n'existait pas."""
    sorties: dict[int, str] = {}
    a_inviter: list[tuple[int, LigneInvitationEntree]] = []
    vus: set[str] = set()
    for rang, ligne in enumerate(lignes):
        if ligne.dossier_id not in dossiers_du_portefeuille:
            sorties[rang] = "dossier_inconnu"
        elif not _FORME_EMAIL.match(ligne.email.strip()):
            sorties[rang] = "email_invalide"
        elif ligne.dossier_id in vus:
            sorties[rang] = "doublon_dans_le_lot"
        else:
            vus.add(ligne.dossier_id)
            a_inviter.append((rang, ligne))

    existants = comptes.statuts([DossierId(ligne.dossier_id) for _, ligne in a_inviter])
    for rang, ligne in a_inviter:
        if ligne.dossier_id in existants:
            sorties[rang] = "deja_invite"
            continue
        try:
            comptes.inviter(
                DossierId(ligne.dossier_id), ligne.email.strip(), verifier_existant=False
            )
        except Exception:  # noqa: BLE001 — le détail (adresse) n'est pas renvoyé au client
            sorties[rang] = "erreur"
        else:
            sorties[rang] = "invité"

    vues = [
        LigneInvitationVue(dossier_id=ligne.dossier_id, email=ligne.email, resultat=sorties[rang])
        for rang, ligne in enumerate(lignes)
    ]
    return InvitationsMasseVue(lignes=vues, nb_invitees=sum(v.resultat == "invité" for v in vues))


def _fichier(contenu: bytes | str, media_type: str, nom_fichier: str) -> Response:
    corps = contenu.encode("utf-8") if isinstance(contenu, str) else contenu
    return Response(
        content=corps,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


def _enregistrer_routes_cloture(app: FastAPI) -> None:
    """Semaine 4 (doc 17 §9) : les renderers de clôture, exposés en
    téléchargement direct — sur le ledger avec décisions humaines appliquées
    (`_construire_liasse`), pas le ledger brut."""

    @app.get("/dossiers/{dossier_id}/liasse.pdf")
    def telecharger_liasse(dossier: DossierDep, ledger: LedgerDossierDep) -> Response:
        pdf = PdfLiasseSimplifieeRenderer().rendre(_construire_liasse(dossier, ledger))
        return _fichier(pdf, "application/pdf", f"liasse-{dossier.id}.pdf")

    @app.get("/dossiers/{dossier_id}/cerfa-2065.pdf")
    def telecharger_cerfa(dossier: DossierDep, ledger: LedgerDossierDep) -> Response:
        pdf = PdfCerfa2065Renderer().rendre(_construire_liasse(dossier, ledger))
        return _fichier(pdf, "application/pdf", f"cerfa-2065-{dossier.id}.pdf")

    @app.get("/dossiers/{dossier_id}/fec.txt")
    def telecharger_fec(dossier: DossierDep, ledger: LedgerDossierDep) -> Response:
        ecritures = ledger.grand_livre(dossier.id)
        return _fichier(
            exporter_fec(ecritures), "text/plain; charset=utf-8", f"fec-{dossier.id}.txt"
        )

    @app.get("/dossiers/{dossier_id}/grand-livre.csv")
    def telecharger_grand_livre(dossier: DossierDep, ledger: LedgerDossierDep) -> Response:
        ecritures = ledger.grand_livre(dossier.id)
        return _fichier(
            exporter_grand_livre(ecritures), "text/csv", f"grand-livre-{dossier.id}.csv"
        )

    @app.get("/dossiers/{dossier_id}/balance.csv")
    def telecharger_balance(dossier: DossierDep, ledger: LedgerDossierDep) -> Response:
        ecritures = ledger.grand_livre(dossier.id)
        return _fichier(exporter_balance(ecritures), "text/csv", f"balance-{dossier.id}.csv")


def _document_greffe_inpi(dossier: Dossier, ledger: InMemoryLedgerService) -> bytes:
    """doc 20 §4 : le PDF non signé (« document de synthèse » de démo, pas
    celui que le Guichet Unique génère réellement — on ne peut pas
    l'appeler sans compte e-procédures)."""
    return PdfDepotInpiRenderer().rendre(_construire_liasse(dossier, ledger))


def _enregistrer_routes_greffe_inpi(app: FastAPI) -> None:
    """doc 20 §4/§5, Louis 2026-09-11 : signature fictive pour la démo
    (jamais qualifiée RGS, `qualifie=False`), mais une vraie zone de
    signature qui finit le document — pas juste un badge React. Le vrai
    dépôt (appel API + signature qualifiée réelle) reste bloqué sur
    ADR-004 (prestataire, doc 20 §7)."""

    @app.get("/dossiers/{dossier_id}/greffe-inpi.pdf")
    def telecharger_greffe_inpi(
        dossier: DossierDep, ledger: LedgerDossierDep, signatures: SignaturesInpiDep
    ) -> Response:
        document_signe = signatures.dernier(dossier.id, TYPE_DOCUMENT_GREFFE_INPI)
        pdf = (
            document_signe.contenu_pdf
            if document_signe is not None
            else _document_greffe_inpi(dossier, ledger)
        )
        return _fichier(pdf, "application/pdf", f"greffe-inpi-{dossier.id}.pdf")

    @app.post("/dossiers/{dossier_id}/greffe-inpi/signature", response_model=SignatureGreffeVue)
    def signer_greffe_inpi(
        dossier: DossierDep,
        ledger: LedgerDossierDep,
        signatures: SignaturesInpiDep,
        identite: IdentiteDep,
    ) -> SignatureGreffeVue:
        identite = _verifier_acces_dossier(dossier.id, identite)
        pdf_non_signe = _document_greffe_inpi(dossier, ledger)
        document = SignatureDemoProvider().signer(pdf_non_signe, identite.user_id)
        signatures.enregistrer(dossier.id, TYPE_DOCUMENT_GREFFE_INPI, document)
        return SignatureGreffeVue(
            dossier_id=dossier.id,
            signe=True,
            signe_le=document.signe_le.isoformat(),
            qualifie=document.qualifie,
        )


def create_app() -> FastAPI:
    app = FastAPI(title="AxeLCompta — démo produit (API)", version="0.0.1")
    _configurer_cors(app)
    _enregistrer_routes_dossiers(app)
    _enregistrer_routes_transactions(app)
    _enregistrer_routes_invitation(app)
    _enregistrer_routes_cloture(app)
    _enregistrer_routes_greffe_inpi(app)
    return app


app = create_app()
