"""API FastAPI dédiée à la démo produit (doc 17 §9 semaine 2, doc 19) — sert
les 3 chauffeurs type au frontend Next.js.

Distincte de `axelcompta.api` (la vraie API produit, doc 03 §7, encore un
squelette sans route) : ceci est une composition root comme
`demo_chauffeurs_type.py` (doc 18), pas soumise aux mêmes contraintes de
dépendance qu'un module métier — elle peut importer n'importe quoi
directement, y compris une autre composition root.

**Lecture seule pour l'instant** (dashboard + détail dossier + liste des
transactions). La vraie décision humaine sur la file de revue (accepter/
reclasser une écriture « à trancher », doc 11 §3.1/§3.2) est la prochaine
étape (doc 17 §9 semaine 2) — pas encore câblée ici, volontairement : mieux
vaut un écran de lecture réel qu'une décision à moitié faite.

Pas de persistance : chaque requête reconstruit le ledger depuis le
générateur déterministe (`chauffeurs_demo.py`), comme les autres
composition roots de démo. Suffisant pour 3 dossiers de quelques centaines
d'écritures chacun — pas un choix qui tiendrait pour 200 dossiers réels.

Usage : `uvicorn axelcompta.demo_api:app --reload --port 8000` depuis
backend/ (nécessite `pip install -e ".[dev]"` pour uvicorn).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from axelcompta.closing.bilan_simplifie import ClotureSimplifieeService
from axelcompta.demo_chauffeurs_type import construire_ledger
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO, ProfilChauffeurType
from axelcompta.ledger.models import Ecriture, Sens

COMPTE_ATTENTE = "471"  # doc 06 §2 : compte d'attente par défaut, "à trancher"
ORIGINE_FRONTEND_DEV = "http://localhost:3000"


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


class TransactionVue(BaseModel):
    ecriture_id: str
    date: str
    libelle: str
    montant_cts: int  # signé : positif = argent reçu, négatif = argent sorti (ligne 512)
    compte: str
    statut: str  # "validé" | "à trancher" — vocabulaire unique de badge (doc 11 §4)


def _profil_par_id(dossier_id: str) -> ProfilChauffeurType:
    for profil in PROFILS_DEMO:
        if profil.dossier_id == dossier_id:
            return profil
    raise HTTPException(status_code=404, detail=f"Dossier inconnu : {dossier_id}")


def _resume(profil: ProfilChauffeurType) -> DossierResume:
    ledger = construire_ledger(profil)
    ecritures = ledger.grand_livre(profil.dossier_id)
    liasse = ClotureSimplifieeService(ledger).cloturer(
        profil.dossier_id, exercice=str(profil.date_debut.year)
    )
    nb_a_trancher = sum(
        1 for e in ecritures if any(ligne.compte == COMPTE_ATTENTE for ligne in e.lignes)
    )
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


def create_app() -> FastAPI:
    app = FastAPI(title="AxeLCompta — démo produit (API)", version="0.0.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGINE_FRONTEND_DEV],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/dossiers", response_model=list[DossierResume])
    def lister_dossiers() -> list[DossierResume]:
        return [_resume(profil) for profil in PROFILS_DEMO]

    @app.get("/dossiers/{dossier_id}", response_model=DossierResume)
    def obtenir_dossier(dossier_id: str) -> DossierResume:
        return _resume(_profil_par_id(dossier_id))

    @app.get("/dossiers/{dossier_id}/transactions", response_model=list[TransactionVue])
    def lister_transactions(dossier_id: str) -> list[TransactionVue]:
        profil = _profil_par_id(dossier_id)
        ledger = construire_ledger(profil)
        return [_transaction_vue(e) for e in ledger.grand_livre(profil.dossier_id)]

    return app


app = create_app()
