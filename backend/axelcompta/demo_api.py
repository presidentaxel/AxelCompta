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

Transactions, écritures générées et liasse restent recalculées à la volée
depuis `chauffeurs_demo.py` à chaque requête (déterministe, pas de coût à
persister ça pour 3 dossiers) — seules les décisions humaines et leurs
annotations dev survivent entre deux requêtes, réappliquées par-dessus le
ledger recalculé (`_ledger_avec_decisions`).

Usage : `uvicorn axelcompta.demo_api:app --reload --port 8000` depuis
backend/ (nécessite `pip install -e ".[dev]"` pour uvicorn).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.core.db import engine_depuis_env
from axelcompta.core.ids import EcritureId, UserId
from axelcompta.demo_chauffeurs_type import construire_ledger
from axelcompta.demo_comptes import (
    CompteDejaInviteError,
    CompteRepository,
    StatutInvitation,
    SupabaseCompteRepository,
    SupabaseConfig,
)
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO, ProfilChauffeurType
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.ledger.models import Ecriture, Sens
from axelcompta.packs.vtc_demo import charger_compte_par_categorie
from axelcompta.workflow.decisions import DecisionHumaine, DecisionRepository
from axelcompta.workflow.decisions_postgres import PostgresDecisionRepository
from axelcompta.workflow.revue import CategorieInconnueError, resoudre_ecriture_a_trancher

COMPTE_ATTENTE = "471"  # doc 06 §2 : compte d'attente par défaut, "à trancher"
ORIGINE_FRONTEND_DEV = "http://localhost:3000"
# doc 17 §9 bloc B (comptes réels) pas encore fait : toute décision de la
# démo est attribuée à cet utilisateur unique en attendant. À retirer dès
# que Supabase Auth est branché — pas un choix d'architecture, un stub.
UTILISATEUR_DEMO = UserId("gestionnaire_demo")


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


class TransactionVue(BaseModel):
    ecriture_id: str
    date: str
    libelle: str
    montant_cts: int  # signé : positif = argent reçu, négatif = argent sorti (ligne 512)
    compte: str
    statut: str  # "validé" | "à trancher" — vocabulaire unique de badge (doc 11 §4)


class DecisionEntree(BaseModel):
    categorie: str  # "usage_personnel" ou toute catégorie du pack (doc 17 §9 bloc C)


class InvitationEntree(BaseModel):
    email: str  # doc 17 §9 bloc B — pas les 3 profils démo, un vrai e-mail entré à la volée


class InvitationVue(BaseModel):
    dossier_id: str
    email: str
    statut: str  # "invité" | "actif" — jamais "non_invité" ici, ça n'existe qu'en absence


def _profil_par_id(dossier_id: str) -> ProfilChauffeurType:
    for profil in PROFILS_DEMO:
        if profil.dossier_id == dossier_id:
            return profil
    raise HTTPException(status_code=404, detail=f"Dossier inconnu : {dossier_id}")


def _ledger_avec_decisions(
    profil: ProfilChauffeurType, decisions: DecisionRepository
) -> InMemoryLedgerService:
    """Le ledger recalculé (déterministe), avec les décisions humaines
    persistées ré-appliquées par-dessus (doc 17 §9 bloc A/C). C'est la
    seule chose qui doit survivre entre deux requêtes — pas le ledger."""
    ledger, _propositions = construire_ledger(profil)
    dernieres_decisions = {
        decision.ecriture_id: decision
        for decision in decisions.lister_decisions(profil.dossier_id)
    }
    if not dernieres_decisions:
        return ledger

    comptes = charger_compte_par_categorie()
    resultat = InMemoryLedgerService()
    for ecriture in ledger.grand_livre(profil.dossier_id):
        decision = dernieres_decisions.get(ecriture.id)
        if decision is not None:
            ecriture = resoudre_ecriture_a_trancher(
                ecriture, decision.categorie, profil.forme_juridique, comptes
            )
        resultat.enregistrer(ecriture)
    return resultat


def _statut_invitation_vue(statut: StatutInvitation) -> str:
    return {StatutInvitation.INVITE: "invité", StatutInvitation.ACTIF: "actif"}[statut]


def _resume(
    profil: ProfilChauffeurType, decisions: DecisionRepository, comptes: CompteRepository
) -> DossierResume:
    ledger = _ledger_avec_decisions(profil, decisions)
    ecritures = ledger.grand_livre(profil.dossier_id)
    liasse = ClotureSimplifieeService(ledger).cloturer(
        profil.dossier_id, exercice=str(profil.date_debut.year)
    )
    nb_a_trancher = sum(
        1 for e in ecritures if any(ligne.compte == COMPTE_ATTENTE for ligne in e.lignes)
    )
    invitation = comptes.statut(profil.dossier_id)
    return DossierResume(
        dossier_id=profil.dossier_id,
        nom=profil.nom,
        tva_recettes_regime=profil.tva_recettes_regime,
        plateformes=[p.nom for p in profil.plateformes],
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
    )


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


def _transaction_vue(ecriture: Ecriture) -> TransactionVue:
    a_trancher = any(ligne.compte == COMPTE_ATTENTE for ligne in ecriture.lignes)
    return TransactionVue(
        ecriture_id=ecriture.id,
        date=ecriture.date.isoformat(),
        libelle=ecriture.libelle,
        montant_cts=_montant_512(ecriture),
        compte=_compte_affiche(ecriture),
        statut="à trancher" if a_trancher else "validé",
    )


_ENGINE_DEMO: Engine | None = None


def get_decisions() -> DecisionRepository:
    """Dépendance FastAPI — construit l'engine Postgres **à la première
    requête réelle**, pas à l'import du module : importer `demo_api` (pour
    ses tests, par exemple) ne doit pas exiger `DATABASE_URL`. Les tests
    surchargent cette dépendance
    (`app.dependency_overrides[get_decisions] = ...`) avec
    `InMemoryDecisionRepository` pour ne jamais l'appeler du tout."""
    global _ENGINE_DEMO
    if _ENGINE_DEMO is None:
        _ENGINE_DEMO = engine_depuis_env()
    return PostgresDecisionRepository(_ENGINE_DEMO)


DecisionsDep = Annotated[DecisionRepository, Depends(get_decisions)]


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


def _trancher(
    profil: ProfilChauffeurType, ecriture_id: str, categorie: str, decisions: DecisionRepository
) -> Ecriture:
    """doc 17 §9 bloc C : la décision humaine, pour de vrai — déclenche le
    `workflow` testé (doc 05 §5), pas un changement d'état côté React seul.
    Extrait de la route (doc 08 §2 : longueur de fonction) plutôt que fait
    inline."""
    ledger, propositions = construire_ledger(profil)
    ecriture = next(
        (e for e in ledger.grand_livre(profil.dossier_id) if e.id == ecriture_id), None
    )
    if ecriture is None:
        raise HTTPException(status_code=404, detail=f"Écriture inconnue : {ecriture_id}")
    if decisions.decision_courante(profil.dossier_id, EcritureId(ecriture_id)) is not None:
        raise HTTPException(
            status_code=409,
            detail="Cette écriture a déjà été tranchée (doc 05 §5 : décision immuable).",
        )
    if not any(ligne.compte == COMPTE_ATTENTE for ligne in ecriture.lignes):
        raise HTTPException(status_code=409, detail="Cette écriture n'est pas à trancher.")
    proposition = propositions.get(EcritureId(ecriture_id))
    if proposition is None:
        raise HTTPException(
            status_code=500,
            detail="Aucune proposition d'origine pour cette écriture (incohérence interne).",
        )
    comptes = charger_compte_par_categorie()
    try:
        resoudre_ecriture_a_trancher(ecriture, categorie, profil.forme_juridique, comptes)
    except CategorieInconnueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    decisions.enregistrer_decision(
        DecisionHumaine(
            dossier_id=profil.dossier_id,
            ecriture_id=EcritureId(ecriture_id),
            categorie=categorie,
            etage_origine=proposition.etage,
            confiance_origine=proposition.confiance,
            decide_par=UTILISATEUR_DEMO,
            decide_le=datetime.now(UTC),
        )
    )
    ledger_a_jour = _ledger_avec_decisions(profil, decisions)
    return next(e for e in ledger_a_jour.grand_livre(profil.dossier_id) if e.id == ecriture_id)


def create_app() -> FastAPI:
    app = FastAPI(title="AxeLCompta — démo produit (API)", version="0.0.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGINE_FRONTEND_DEV],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/dossiers", response_model=list[DossierResume])
    def lister_dossiers(decisions: DecisionsDep, comptes: ComptesDep) -> list[DossierResume]:
        return [_resume(profil, decisions, comptes) for profil in PROFILS_DEMO]

    @app.get("/dossiers/{dossier_id}", response_model=DossierResume)
    def obtenir_dossier(
        dossier_id: str, decisions: DecisionsDep, comptes: ComptesDep
    ) -> DossierResume:
        return _resume(_profil_par_id(dossier_id), decisions, comptes)

    @app.get("/dossiers/{dossier_id}/transactions", response_model=list[TransactionVue])
    def lister_transactions(dossier_id: str, decisions: DecisionsDep) -> list[TransactionVue]:
        profil = _profil_par_id(dossier_id)
        ledger = _ledger_avec_decisions(profil, decisions)
        return [_transaction_vue(e) for e in ledger.grand_livre(profil.dossier_id)]

    @app.post(
        "/dossiers/{dossier_id}/transactions/{ecriture_id}/decision",
        response_model=TransactionVue,
    )
    def trancher_transaction(
        dossier_id: str,
        ecriture_id: str,
        entree: DecisionEntree,
        decisions: DecisionsDep,
    ) -> TransactionVue:
        profil = _profil_par_id(dossier_id)
        ecriture = _trancher(profil, ecriture_id, entree.categorie, decisions)
        return _transaction_vue(ecriture)

    @app.post("/dossiers/{dossier_id}/inviter", response_model=InvitationVue)
    def inviter_chauffeur(
        dossier_id: str, entree: InvitationEntree, comptes: ComptesDep
    ) -> InvitationVue:
        """doc 17 §9 bloc B, doc 19 §3.1 : le gestionnaire invite, jamais
        de self-signup (disable_signup, vérifié 2026-09-07). Envoie un
        vrai e-mail via Supabase Auth — pas un simulateur."""
        profil = _profil_par_id(dossier_id)
        try:
            invitation = comptes.inviter(profil.dossier_id, entree.email)
        except CompteDejaInviteError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return InvitationVue(
            dossier_id=invitation.dossier_id,
            email=invitation.email,
            statut=_statut_invitation_vue(invitation.statut),
        )

    return app


app = create_app()
