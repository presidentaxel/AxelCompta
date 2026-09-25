"""Teste l'API démo (doc 17 §9). `get_decisions`/`get_comptes` sont
surchargées avec les implémentations en mémoire (`dependency_overrides`,
idiome FastAPI) : la suite rapide vérifie le contrat HTTP sans jamais
construire d'engine Postgres ni appeler Supabase —
`tests/integration/test_decisions_repository.py` et
`tests/integration/test_comptes_supabase.py` prouvent séparément que les
implémentations réelles respectent le même contrat.

**Depuis le 2026-09-11 (doc 19 §8bis)** : toutes les routes de niveau
dossier exigent un jeton indiv valide — `_en_tete(dossier_id)` en fournit
un partout où c'était avant un appel anonyme (ancien comportement
« gestionnaire sans login »).
"""

from __future__ import annotations

import functools
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import axelcompta.demo_auth as demo_auth
import axelcompta.demo_seed as demo_seed
from axelcompta.core.ids import DossierId, EcritureId, TenantId
from axelcompta.demo_api import (
    DossierResume,
    _frises,
    create_app,
    get_comptes,
    get_decisions,
    get_dossiers,
    get_justificatifs,
    get_ledger,
    get_propositions,
    get_role_membre,
    get_signatures_inpi,
)
from axelcompta.demo_chauffeurs_type import construire_ledger
from axelcompta.demo_comptes_memory import InMemoryCompteRepository
from axelcompta.demo_justificatifs import InMemoryJustificatifRepository
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO
from axelcompta.ledger.contrepassation import contrepasser
from axelcompta.ledger.memory import InMemoryLedgerService
from axelcompta.tenants.memory import InMemoryDossierRepository
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.workflow.decisions_memory import InMemoryDecisionRepository
from axelcompta.workflow.propositions import InMemoryPropositionRepository
from axelcompta.workflow.signature_memory import InMemorySignatureRepository

# ES256 (JWT Signing Keys), pas HS256 : ce qu'émet le vrai projet Supabase
# (découvert 2026-09-08, voir le commentaire de module de demo_auth.py).
_CLE_PRIVEE_TEST = ec.generate_private_key(ec.SECP256R1())


def _jeton_chauffeur(dossier_id: str) -> str:
    charge_utile = {
        "sub": "user-123",
        "email": "chauffeur@example.com",
        "aud": "authenticated",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "app_metadata": {"dossier_id": dossier_id},
    }
    return jwt.encode(charge_utile, _CLE_PRIVEE_TEST, algorithm="ES256")


def _jeton_gestionnaire(tenant_id: str = "TENANT_DEMO", dossier_id: str | None = None) -> str:
    """doc 03 §7 : le lien gestionnaire vit dans `app_metadata` (écrit côté
    serveur), pas `user_metadata` (modifiable par l'utilisateur)."""
    charge_utile: dict[str, object] = {
        "sub": "gestionnaire-1",
        "email": "gestionnaire@example.com",
        "aud": "authenticated",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "app_metadata": {"tenant_id": tenant_id},
    }
    if dossier_id is not None:
        charge_utile["app_metadata"]["dossier_id"] = dossier_id  # type: ignore[index]
    return jwt.encode(charge_utile, _CLE_PRIVEE_TEST, algorithm="ES256")


def _en_tete_gestionnaire(
    tenant_id: str = "TENANT_DEMO", dossier_id: str | None = None
) -> dict[str, str]:
    return {"Authorization": f"Bearer {_jeton_gestionnaire(tenant_id, dossier_id)}"}


def _en_tete(dossier_id: str) -> dict[str, str]:
    """doc 19 §8bis : jeton indiv valide, scopé sur `dossier_id`."""
    return {"Authorization": f"Bearer {_jeton_chauffeur(dossier_id)}"}


@pytest.fixture(autouse=True)
def _ledger_calcule_une_seule_fois(monkeypatch: pytest.MonkeyPatch) -> None:
    """L'amorçage recalcule le ledger des 3 profils (réconciliation + ML) ;
    le résultat est déterministe, donc calculé une fois pour toute la suite
    plutôt qu'à chaque client de test."""
    monkeypatch.setattr(demo_seed, "construire_ledger", _construire_ledger_en_cache)


@functools.cache
def _construire_ledger_en_cache(profil):  # type: ignore[no-untyped-def]
    return construire_ledger(profil)


@pytest.fixture(autouse=True)
def _jwks_factice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bouchon de résolution JWKS pour toute la suite — pas d'appel réseau
    à Supabase (même logique que les autres dépendances de démo)."""
    monkeypatch.setenv("SUPABASE_URL", "https://exemple.supabase.co")
    cle_publique = _CLE_PRIVEE_TEST.public_key()
    monkeypatch.setattr(
        demo_auth,
        "_jwks_client",
        lambda url: SimpleNamespace(
            get_signing_key_from_jwt=lambda jeton: SimpleNamespace(key=cle_publique)
        ),
    )


def _client_et_stubs(
    role: str = "admin",
) -> tuple[TestClient, InMemoryDecisionRepository, InMemoryJustificatifRepository]:
    app = create_app()
    # Même instance à chaque requête (pas juste la classe : une nouvelle
    # instance par requête serait vide à chaque fois) — une décision ou une
    # invitation doit rester visible sur les GET suivants du même client,
    # comme le font les vraies dépendances via leur connexion partagée.
    decisions_stub = InMemoryDecisionRepository()
    comptes_stub = InMemoryCompteRepository()
    justificatifs_stub = InMemoryJustificatifRepository()
    # `get_signatures_inpi` parle à Postgres en vrai — surchargé ici pour
    # que la suite rapide n'ouvre pas de connexion, et pour isoler les tests.
    signatures_stub = InMemorySignatureRepository()
    dossiers_stub = InMemoryDossierRepository()
    ledger_stub = InMemoryLedgerService()
    propositions_stub = InMemoryPropositionRepository()
    demo_seed.amorcer_demo(dossiers_stub, ledger_stub, propositions_stub)
    # Un second portefeuille, vide : sert aux tests d'isolation entre tenants.
    dossiers_stub.enregistrer_tenant(Tenant(id=TenantId("AUTRE_TENANT"), nom="Autre"))
    app.dependency_overrides[get_dossiers] = lambda: dossiers_stub
    app.dependency_overrides[get_ledger] = lambda: ledger_stub
    app.dependency_overrides[get_propositions] = lambda: propositions_stub
    app.dependency_overrides[get_decisions] = lambda: decisions_stub
    app.dependency_overrides[get_comptes] = lambda: comptes_stub
    app.dependency_overrides[get_justificatifs] = lambda: justificatifs_stub
    app.dependency_overrides[get_signatures_inpi] = lambda: signatures_stub
    # `droits_membre` est en Postgres : le rôle est fixé ici.
    app.dependency_overrides[get_role_membre] = lambda: role
    return TestClient(app), decisions_stub, justificatifs_stub


def _client() -> TestClient:
    return _client_et_stubs()[0]


def test_lister_dossiers_retourne_les_3_chauffeurs_type() -> None:
    reponse = _client().get("/dossiers", headers=_en_tete_gestionnaire())
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps) == 3
    assert {d["dossier_id"] for d in corps} == {p.dossier_id for p in PROFILS_DEMO}


def _resume_actif(greffe_signe: bool) -> DossierResume:
    return DossierResume(
        dossier_id="D",
        nom="D",
        tva_recettes_regime="franchise",
        plateformes=[],
        exercice_debut=None,
        exercice_fin=None,
        ca_ht_cts=0,
        charges_cts=0,
        resultat_cts=0,
        tresorerie_cts=0,
        tva_a_payer_cts=0,
        nb_transactions=0,
        nb_a_trancher=0,
        statut_invitation="actif",
        mode_acces_bancaire="gestionnaire",
        greffe_inpi_signe=greffe_signe,
    )


def _dossier_finissant_le(fin: date) -> Dossier:
    return Dossier(
        id=DossierId("D"),
        tenant_id=TenantId("T"),
        forme_juridique="SASU",
        regime_imposition="IS",
        regime_tva="franchise",
        nom="D",
        tva_recettes_regime="franchise",
        exercice_debut=fin - timedelta(days=364),
        exercice_fin=fin,
    )


def test_frise_davant_suit_les_preuves_dans_l_ordre() -> None:
    """Exercice clos au 31/12 : l'année suivante, on le traite. Sa frise
    avance avec les preuves, dans l'ordre, et un trou ne saute pas d'étape.
    L'année en cours ne montre que le compte."""
    fin = date(datetime.now(UTC).year - 1, 12, 31)
    dossier = _dossier_finissant_le(fin)
    resume = _resume_actif(False)

    assert _frises(resume, dossier, set()) == (fin.year + 1, "Suivi", fin.year, "Suivi")
    assert _frises(resume, dossier, {"cloture"}) == (fin.year + 1, "Suivi", fin.year, "Clôture")
    assert _frises(resume, dossier, {"cloture", "validation_comptes"}) == (
        fin.year + 1,
        "Suivi",
        fin.year,
        "Signature",
    )
    assert _frises(resume, dossier, {"cloture", "validation_comptes", "greffe_inpi"}) == (
        fin.year + 1,
        "Suivi",
        fin.year,
        "Greffe",
    )
    # Le greffe seul ne coche pas les étapes d'avant.
    assert _frises(resume, dossier, {"greffe_inpi"}) == (fin.year + 1, "Suivi", fin.year, "Suivi")


def test_frise_sans_exercice_davant_si_lexercice_nest_pas_termine() -> None:
    fin = datetime.now(UTC).date() + timedelta(days=30)

    frises = _frises(_resume_actif(True), _dossier_finissant_le(fin), set())

    assert frises == (fin.year, "Suivi", fin.year - 1, "Sans exercice")


def test_aucune_frise_nest_cochee_doffice() -> None:
    corps = _client().get("/dossiers", headers=_en_tete_gestionnaire()).json()
    assert all(d["etape_precedente"] != "Clos" for d in corps)


def test_lister_dossiers_sans_jeton_est_refuse() -> None:
    """Avant le 2026-09-21 cette route était ouverte à tous et renvoyait le
    CA/résultat/trésorerie des 3 dossiers."""
    assert _client().get("/dossiers").status_code == 401


def test_lister_dossiers_avec_jeton_indiv_seul_est_refuse() -> None:
    """Un chauffeur n'a pas le lien `tenant_id` : il ne voit pas le portefeuille."""
    reponse = _client().get("/dossiers", headers=_en_tete("DEMO_karim"))
    assert reponse.status_code == 403


def test_lister_dossiers_autre_tenant_ne_voit_rien_du_portefeuille_demo() -> None:
    """Isolation entre portefeuilles : un gestionnaire d'un autre tenant est
    authentifié mais ne voit aucun dossier qui n'est pas dans le sien."""
    reponse = _client().get("/dossiers", headers=_en_tete_gestionnaire("AUTRE_TENANT"))
    assert reponse.status_code == 200
    assert reponse.json() == []


def test_inviter_un_dossier_dun_autre_portefeuille_est_404() -> None:
    """404 et non 403 : ne pas révéler l'existence de dossiers d'autrui."""
    reponse = _client().post(
        "/dossiers/DEMO_karim/inviter",
        json={"email": "x@example.com"},
        headers=_en_tete_gestionnaire("AUTRE_TENANT"),
    )
    assert reponse.status_code == 404


def test_dossier_inconnu_sans_jeton_reste_401() -> None:
    """L'existence d'un dossier ne fuit pas : 401 avant 404."""
    assert _client().get("/dossiers/INCONNU/transactions").status_code == 401


def test_compte_mono_accede_aux_deux_vues() -> None:
    """doc 03 §7 : le mode mono n'est pas un rôle à part, juste les deux
    liens sur le même compte."""
    client = _client()
    en_tete = _en_tete_gestionnaire(dossier_id="DEMO_karim")
    assert client.get("/dossiers", headers=en_tete).status_code == 200
    assert client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).status_code == 200


def test_gestionnaire_seul_naccede_pas_au_detail_dun_dossier() -> None:
    """doc 19 §2.4 : jamais le détail, quel que soit le dossier."""
    client = _client()
    en_tete = _en_tete_gestionnaire()
    assert client.get("/dossiers/DEMO_karim", headers=en_tete).status_code == 403
    assert client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).status_code == 403
    assert client.get("/dossiers/DEMO_karim/fec.txt", headers=en_tete).status_code == 403


def test_liste_gestionnaire_ne_contient_que_des_agregats() -> None:
    """doc 19 §2.1/§2.4 : CA/charges/résultat et onboarding, rien qui donne
    l'état du détail (nombre de transactions à trancher, trésorerie, TVA à
    payer, statut de signature greffe : tous dérivés de la compta de l'indiv)."""
    corps = _client().get("/dossiers", headers=_en_tete_gestionnaire()).json()
    interdits = {
        "nb_transactions",
        "nb_a_trancher",
        "tresorerie_cts",
        "tva_a_payer_cts",
        "greffe_inpi_signe",
    }
    for dossier in corps:
        assert interdits.isdisjoint(dossier)
        assert {"ca_ht_cts", "charges_cts", "resultat_cts", "statut_invitation"} <= set(dossier)


def test_dossier_yanis_est_bien_en_franchise_et_deficitaire() -> None:
    reponse = _client().get("/dossiers/DEMO_yanis", headers=_en_tete("DEMO_yanis"))
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["tva_recettes_regime"] == "franchise"
    assert corps["resultat_cts"] < 0


def test_dossier_inconnu_retourne_404() -> None:
    """Authentifié pour un dossier qui n'existe pas — la vérification
    d'appartenance passe (le jeton dit bien "DEMO_inconnu"), c'est
    `_profil_par_id` qui renvoie le 404, pas l'auth."""
    reponse = _client().get("/dossiers/DEMO_inconnu", headers=_en_tete("DEMO_inconnu"))
    assert reponse.status_code == 404


def test_dossier_sans_jeton_est_refuse() -> None:
    """doc 19 §8bis (2026-09-11) : remplace l'ancien
    `test_transactions_sans_en_tete_reste_ouvert` — l'accès anonyme aux
    routes de niveau dossier n'existe plus."""
    reponse = _client().get("/dossiers/DEMO_sophie")
    assert reponse.status_code == 401


def test_transactions_sophie_contiennent_des_lignes_a_trancher() -> None:
    reponse = _client().get("/dossiers/DEMO_sophie/transactions", headers=_en_tete("DEMO_sophie"))
    assert reponse.status_code == 200
    transactions = reponse.json()
    a_trancher = [t for t in transactions if t["statut"] == "à trancher"]
    assert len(a_trancher) >= 3  # les dépenses ambiguës, doc 17 §4.2


def test_transaction_a_trancher_pointe_bien_sur_le_compte_471() -> None:
    reponse = _client().get("/dossiers/DEMO_sophie/transactions", headers=_en_tete("DEMO_sophie"))
    a_trancher = [t for t in reponse.json() if t["statut"] == "à trancher"]
    assert all(t["compte"] == "471" for t in a_trancher)


def test_montant_settlement_est_signe_positif_cote_encaissement() -> None:
    reponse = _client().get("/dossiers/DEMO_karim/transactions", headers=_en_tete("DEMO_karim"))
    reglements = [t for t in reponse.json() if t["compte"] == "règlement plateforme"]
    assert reglements
    assert all(t["montant_cts"] > 0 for t in reglements)


def _premiere_a_trancher(client: TestClient, dossier_id: str) -> str:
    transactions = client.get(
        f"/dossiers/{dossier_id}/transactions", headers=_en_tete(dossier_id)
    ).json()
    return str(next(t["ecriture_id"] for t in transactions if t["statut"] == "à trancher"))


def test_trancher_en_usage_personnel_reclasse_vers_le_compte_455() -> None:
    """doc 17 §9 bloc C, doc 06 §3.6 : Sophie est EURL, donc 455."""
    client = _client()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")

    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers=_en_tete("DEMO_sophie"),
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "validé"
    assert corps["compte"] == "455"


def test_trancher_est_reflete_par_un_get_ulterieur() -> None:
    """La décision doit survivre à la requête suivante (doc 17 §9 bloc A) —
    pas un état perdu au prochain recalcul du ledger."""
    client = _client()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers=_en_tete("DEMO_sophie"),
    )

    transactions = client.get(
        "/dossiers/DEMO_sophie/transactions", headers=_en_tete("DEMO_sophie")
    ).json()
    ecriture = next(t for t in transactions if t["ecriture_id"] == ecriture_id)
    assert ecriture["statut"] == "validé"
    assert ecriture["compte"] == "455"


def test_trancher_diminue_le_compteur_nb_a_trancher() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_sophie")
    avant = client.get("/dossiers/DEMO_sophie", headers=en_tete).json()["nb_a_trancher"]
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")

    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers=en_tete,
    )

    apres = client.get("/dossiers/DEMO_sophie", headers=en_tete).json()["nb_a_trancher"]
    assert apres == avant - 1


def test_trancher_deux_fois_la_meme_ecriture_est_refuse() -> None:
    """doc 05 §5 : la décision humaine est immuable, pas de deuxième
    écriture qui l'écrase silencieusement."""
    client = _client()
    en_tete = _en_tete("DEMO_sophie")
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers=en_tete,
    )

    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "carburant"},
        headers=en_tete,
    )

    assert reponse.status_code == 409


def test_trancher_une_ecriture_deja_validee_est_refuse() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    validees = [
        t
        for t in client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()
        if t["statut"] == "validé"
    ]
    reponse = client.post(
        f"/dossiers/DEMO_karim/transactions/{validees[0]['ecriture_id']}/decision",
        json={"categorie": "usage_personnel"},
        headers=en_tete,
    )
    assert reponse.status_code == 409


def test_trancher_une_ecriture_inconnue_est_un_404() -> None:
    client = _client()
    reponse = client.post(
        "/dossiers/DEMO_sophie/transactions/ecriture-inconnue/decision",
        json={"categorie": "usage_personnel"},
        headers=_en_tete("DEMO_sophie"),
    )
    assert reponse.status_code == 404


def test_trancher_vers_une_categorie_inconnue_est_un_400() -> None:
    client = _client()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "categorie_qui_nexiste_pas"},
        headers=_en_tete("DEMO_sophie"),
    )
    assert reponse.status_code == 400


def test_dossier_jamais_invite_a_un_statut_invitation_null() -> None:
    reponse = _client().get("/dossiers/DEMO_karim", headers=_en_tete("DEMO_karim"))
    assert reponse.json()["statut_invitation"] is None


def test_inviter_chauffeur_renvoie_le_statut_invite() -> None:
    """doc 19 §6 : action gestionnaire, jeton avec lien `tenant_id` requis."""
    client = _client()
    reponse = client.post(
        "/dossiers/DEMO_karim/inviter",
        json={"email": "karim@example.com"},
        headers=_en_tete_gestionnaire(),
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps == {"dossier_id": "DEMO_karim", "email": "karim@example.com", "statut": "invité"}


def test_inviter_est_reflete_par_un_get_ulterieur() -> None:
    """doc 19 §3.2 : le statut d'invitation doit apparaître au dashboard,
    pas seulement dans la réponse du POST."""
    client = _client()
    client.post(
        "/dossiers/DEMO_karim/inviter",
        json={"email": "karim@example.com"},
        headers=_en_tete_gestionnaire(),
    )

    reponse = client.get("/dossiers", headers=_en_tete_gestionnaire())

    karim = next(d for d in reponse.json() if d["dossier_id"] == "DEMO_karim")
    assert karim["statut_invitation"] == "invité"


def test_inviter_deux_fois_le_meme_dossier_est_refuse() -> None:
    client = _client()
    en_tete = _en_tete_gestionnaire()
    client.post(
        "/dossiers/DEMO_karim/inviter", json={"email": "karim@example.com"}, headers=en_tete
    )

    reponse = client.post(
        "/dossiers/DEMO_karim/inviter", json={"email": "autre@example.com"}, headers=en_tete
    )

    assert reponse.status_code == 409


def test_inviter_sans_jeton_est_refuse() -> None:
    reponse = _client().post("/dossiers/DEMO_karim/inviter", json={"email": "x@example.com"})
    assert reponse.status_code == 401


def test_inviter_avec_jeton_indiv_est_refuse() -> None:
    """Un chauffeur ne peut pas inviter (ni s'inviter lui-même, ni un tiers)."""
    reponse = _client().post(
        "/dossiers/DEMO_karim/inviter",
        json={"email": "x@example.com"},
        headers=_en_tete("DEMO_karim"),
    )
    assert reponse.status_code == 403


def test_inviter_en_lecture_seule_est_refuse() -> None:
    client = _client_et_stubs(role="lecture")[0]
    reponse = client.post(
        "/dossiers/DEMO_karim/inviter",
        json={"email": "karim@example.com"},
        headers=_en_tete_gestionnaire(),
    )
    assert reponse.status_code == 403
    lignes = [{"dossier_id": "DEMO_karim", "email": "karim@example.com"}]
    assert _en_masse(client, lignes).status_code == 403


def test_inviter_dossier_inconnu_est_404_pour_un_gestionnaire() -> None:
    reponse = _client().post(
        "/dossiers/INCONNU/inviter",
        json={"email": "x@example.com"},
        headers=_en_tete_gestionnaire(),
    )
    assert reponse.status_code == 404


def test_karim_est_en_mode_chauffeur_direct_les_autres_en_gestionnaire() -> None:
    """doc 19 §4 : les deux modes doivent être représentés dans la démo."""
    corps = {
        p["dossier_id"]: p
        for p in _client().get("/dossiers", headers=_en_tete_gestionnaire()).json()
    }
    assert corps["DEMO_karim"]["mode_acces_bancaire"] == "chauffeur_direct"
    assert corps["DEMO_sophie"]["mode_acces_bancaire"] == "gestionnaire"
    assert corps["DEMO_yanis"]["mode_acces_bancaire"] == "gestionnaire"


def test_chauffeur_authentifie_voit_son_propre_dossier() -> None:
    jeton = _jeton_chauffeur("DEMO_karim")
    reponse = _client().get(
        "/dossiers/DEMO_karim/transactions", headers={"Authorization": f"Bearer {jeton}"}
    )
    assert reponse.status_code == 200


def test_chauffeur_authentifie_ne_voit_pas_un_autre_dossier() -> None:
    jeton = _jeton_chauffeur("DEMO_karim")
    reponse = _client().get(
        "/dossiers/DEMO_sophie/transactions", headers={"Authorization": f"Bearer {jeton}"}
    )
    assert reponse.status_code == 403


# --- doc 17 §9 Semaine 3 : le chauffeur peut trancher sa propre écriture
# (doc 19 §5.6, « question de catégorisation ») — ouvert au chauffeur le
# 2026-09-09, restait gestionnaire-only jusque-là.


def test_chauffeur_authentifie_peut_trancher_sa_propre_ecriture() -> None:
    client, _decisions, _justificatifs = _client_et_stubs()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    jeton = _jeton_chauffeur("DEMO_sophie")

    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers={"Authorization": f"Bearer {jeton}"},
    )

    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "validé"


def test_chauffeur_authentifie_ne_peut_pas_trancher_un_autre_dossier() -> None:
    client, _decisions, _justificatifs = _client_et_stubs()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    jeton = _jeton_chauffeur("DEMO_karim")  # un autre dossier que Sophie

    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers={"Authorization": f"Bearer {jeton}"},
    )

    assert reponse.status_code == 403


def test_decision_chauffeur_est_attribuee_a_sa_vraie_identite() -> None:
    """`decide_par` doit refléter le compte qui a vraiment répondu (doc 05
    §5 : traçabilité) — plus de stub possible depuis le 2026-09-11, un
    jeton est désormais obligatoire (doc 19 §8bis)."""
    client, decisions, _justificatifs = _client_et_stubs()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    jeton = _jeton_chauffeur("DEMO_sophie")

    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers={"Authorization": f"Bearer {jeton}"},
    )

    decision = decisions.decision_courante(DossierId("DEMO_sophie"), EcritureId(ecriture_id))
    assert decision is not None
    assert decision.decide_par == "user-123"  # sub du jeton (_jeton_chauffeur)


# --- doc 17 §9 Semaine 3, doc 19 §5.7 : photo de justificatif, pas d'OCR.


def test_joindre_justificatif_image_valide_marque_la_transaction() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    ecriture_id = client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()[0][
        "ecriture_id"
    ]

    reponse = client.post(
        f"/dossiers/DEMO_karim/transactions/{ecriture_id}/justificatif",
        files={"fichier": ("ticket.jpg", b"contenu-photo-factice", "image/jpeg")},
        headers=en_tete,
    )

    assert reponse.status_code == 200
    assert reponse.json()["a_justificatif"] is True


def test_justificatif_est_reflete_par_un_get_ulterieur() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    ecriture_id = client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()[0][
        "ecriture_id"
    ]
    client.post(
        f"/dossiers/DEMO_karim/transactions/{ecriture_id}/justificatif",
        files={"fichier": ("ticket.jpg", b"contenu-photo-factice", "image/jpeg")},
        headers=en_tete,
    )

    transactions = client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()
    ecriture = next(t for t in transactions if t["ecriture_id"] == ecriture_id)
    assert ecriture["a_justificatif"] is True


def test_autres_transactions_restent_sans_justificatif() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    transactions = client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()
    ecriture_id = transactions[0]["ecriture_id"]
    client.post(
        f"/dossiers/DEMO_karim/transactions/{ecriture_id}/justificatif",
        files={"fichier": ("ticket.jpg", b"contenu-photo-factice", "image/jpeg")},
        headers=en_tete,
    )

    apres = client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()
    autres = [t for t in apres if t["ecriture_id"] != ecriture_id]
    assert autres  # sinon le test ne prouve rien
    assert all(t["a_justificatif"] is False for t in autres)


def test_joindre_justificatif_type_invalide_est_refuse() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    ecriture_id = client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()[0][
        "ecriture_id"
    ]

    reponse = client.post(
        f"/dossiers/DEMO_karim/transactions/{ecriture_id}/justificatif",
        files={"fichier": ("notes.txt", b"pas une photo", "text/plain")},
        headers=en_tete,
    )

    assert reponse.status_code == 400


def test_joindre_justificatif_ecriture_inconnue_est_un_404() -> None:
    reponse = _client().post(
        "/dossiers/DEMO_karim/transactions/ecriture-inconnue/justificatif",
        files={"fichier": ("ticket.jpg", b"contenu-photo-factice", "image/jpeg")},
        headers=_en_tete("DEMO_karim"),
    )
    assert reponse.status_code == 404


def test_chauffeur_peut_joindre_justificatif_a_sa_propre_transaction() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    ecriture_id = client.get("/dossiers/DEMO_karim/transactions", headers=en_tete).json()[0][
        "ecriture_id"
    ]

    reponse = client.post(
        f"/dossiers/DEMO_karim/transactions/{ecriture_id}/justificatif",
        files={"fichier": ("ticket.jpg", b"contenu-photo-factice", "image/jpeg")},
        headers=en_tete,
    )

    assert reponse.status_code == 200


def test_chauffeur_ne_peut_pas_joindre_justificatif_a_un_autre_dossier() -> None:
    client = _client()
    ecriture_id = client.get(
        "/dossiers/DEMO_sophie/transactions", headers=_en_tete("DEMO_sophie")
    ).json()[0]["ecriture_id"]
    jeton = _jeton_chauffeur("DEMO_karim")  # un autre dossier que Sophie

    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/justificatif",
        files={"fichier": ("ticket.jpg", b"contenu-photo-factice", "image/jpeg")},
        headers={"Authorization": f"Bearer {jeton}"},
    )

    assert reponse.status_code == 403


# --- Semaine 4 (doc 17 §9) : clôture/liasse téléchargeables ---------------


def test_telecharger_liasse_renvoie_un_vrai_pdf() -> None:
    reponse = _client().get("/dossiers/DEMO_karim/liasse.pdf", headers=_en_tete("DEMO_karim"))
    assert reponse.status_code == 200
    assert reponse.headers["content-type"] == "application/pdf"
    assert reponse.content.startswith(b"%PDF")


def test_telecharger_cerfa_renvoie_un_vrai_pdf() -> None:
    reponse = _client().get("/dossiers/DEMO_karim/cerfa-2065.pdf", headers=_en_tete("DEMO_karim"))
    assert reponse.status_code == 200
    assert reponse.headers["content-type"] == "application/pdf"
    assert reponse.content.startswith(b"%PDF")


def test_telecharger_fec_contient_les_colonnes_normees() -> None:
    reponse = _client().get("/dossiers/DEMO_karim/fec.txt", headers=_en_tete("DEMO_karim"))
    assert reponse.status_code == 200
    assert "text/plain" in reponse.headers["content-type"]
    assert "JournalCode" in reponse.text  # doc 06 §6 : en-tête des 18 colonnes FEC


def test_telecharger_grand_livre_et_balance_sont_des_csv() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    grand_livre = client.get("/dossiers/DEMO_karim/grand-livre.csv", headers=en_tete)
    balance = client.get("/dossiers/DEMO_karim/balance.csv", headers=en_tete)
    assert grand_livre.status_code == balance.status_code == 200
    assert grand_livre.headers["content-type"].startswith("text/csv")
    assert balance.headers["content-type"].startswith("text/csv")


def test_telecharger_grand_livre_et_balance_pdf() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    grand_livre = client.get("/dossiers/DEMO_karim/grand-livre.pdf", headers=en_tete)
    balance = client.get("/dossiers/DEMO_karim/balance.pdf", headers=en_tete)
    assert grand_livre.status_code == balance.status_code == 200
    assert grand_livre.headers["content-type"] == "application/pdf"
    assert balance.headers["content-type"] == "application/pdf"
    assert grand_livre.content.startswith(b"%PDF")
    assert balance.content.startswith(b"%PDF")


def test_telecharger_cloture_dossier_inconnu_est_un_404() -> None:
    reponse = _client().get("/dossiers/DEMO_inconnu/liasse.pdf", headers=_en_tete("DEMO_inconnu"))
    assert reponse.status_code == 404


def test_chauffeur_ne_peut_pas_telecharger_la_liasse_dun_autre_dossier() -> None:
    jeton = _jeton_chauffeur("DEMO_karim")
    reponse = _client().get(
        "/dossiers/DEMO_sophie/liasse.pdf", headers={"Authorization": f"Bearer {jeton}"}
    )
    assert reponse.status_code == 403


def test_fec_reflete_une_decision_tranchee_pas_le_ledger_brut() -> None:
    """La liasse téléchargée doit refléter les décisions humaines (bloc A/C,
    doc 17 §9), pas un ledger recalculé sans elles — le compte 455 doit
    apparaître dans le FEC une fois la décision prise, alors qu'il n'y
    figurait pas avant (Sophie n'a jamais de 455 en l'absence de décision,
    seulement du 471 « à trancher »)."""
    client = _client()
    en_tete = _en_tete("DEMO_sophie")
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    avant = client.get("/dossiers/DEMO_sophie/fec.txt", headers=en_tete).text
    # Zone CompteNum exacte : « 455 » seul figure aussi dans 44551 (TVA).
    assert "\t455\t" not in avant

    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers=en_tete,
    )

    apres = client.get("/dossiers/DEMO_sophie/fec.txt", headers=en_tete).text
    assert "\t455\t" in apres


def test_fec_nom_legal_et_ecritures_de_cloture() -> None:
    reponse = _client().get("/dossiers/DEMO_karim/fec.txt", headers=_en_tete("DEMO_karim"))
    assert reponse.status_code == 200
    assert 'filename="987142031FEC20251231.txt"' in reponse.headers["content-disposition"]
    assert "CLOTURE-IS-2025" in reponse.text and "\t695\t" in reponse.text


def test_telecharger_la_liasse_fiscale_complete() -> None:
    reponse = _client().get(
        "/dossiers/DEMO_karim/liasse-fiscale.pdf", headers=_en_tete("DEMO_karim")
    )
    assert reponse.status_code == 200
    assert reponse.content.startswith(b"%PDF-")


# --- Greffe/INPI (doc 20, Louis 2026-09-11) --------------------------------


def test_dossier_resume_greffe_inpi_signe_est_faux_par_defaut() -> None:
    corps = _client().get("/dossiers/DEMO_karim", headers=_en_tete("DEMO_karim")).json()
    assert corps["greffe_inpi_signe"] is False


def test_telecharger_greffe_inpi_renvoie_un_pdf_non_signe_par_defaut() -> None:
    reponse = _client().get("/dossiers/DEMO_karim/greffe-inpi.pdf", headers=_en_tete("DEMO_karim"))
    assert reponse.status_code == 200
    assert reponse.headers["content-type"] == "application/pdf"
    assert reponse.content.startswith(b"%PDF")


def test_signer_greffe_inpi_renvoie_une_signature_non_qualifiee() -> None:
    """doc 20 §4 : jamais une vraie signature qualifiée RGS en démo."""
    reponse = _client().post(
        "/dossiers/DEMO_karim/greffe-inpi/signature", headers=_en_tete("DEMO_karim")
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["signe"] is True
    assert corps["qualifie"] is False


def test_signer_greffe_inpi_est_reflete_par_un_get_ulterieur() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    client.post("/dossiers/DEMO_karim/greffe-inpi/signature", headers=en_tete)

    corps = client.get("/dossiers/DEMO_karim", headers=en_tete).json()
    assert corps["greffe_inpi_signe"] is True


def test_telecharger_greffe_inpi_apres_signature_renvoie_le_pdf_signe() -> None:
    client = _client()
    en_tete = _en_tete("DEMO_karim")
    avant = client.get("/dossiers/DEMO_karim/greffe-inpi.pdf", headers=en_tete).content
    client.post("/dossiers/DEMO_karim/greffe-inpi/signature", headers=en_tete)
    apres = client.get("/dossiers/DEMO_karim/greffe-inpi.pdf", headers=en_tete).content

    assert apres != avant
    assert apres.startswith(b"%PDF")


def test_telecharger_greffe_inpi_dossier_inconnu_est_un_404() -> None:
    reponse = _client().get(
        "/dossiers/DEMO_inconnu/greffe-inpi.pdf", headers=_en_tete("DEMO_inconnu")
    )
    assert reponse.status_code == 404


def test_chauffeur_ne_peut_pas_signer_le_greffe_inpi_dun_autre_dossier() -> None:
    jeton = _jeton_chauffeur("DEMO_karim")
    reponse = _client().post(
        "/dossiers/DEMO_sophie/greffe-inpi/signature",
        headers={"Authorization": f"Bearer {jeton}"},
    )
    assert reponse.status_code == 403


def _en_masse(client: TestClient, lignes: list[dict[str, str]], **kw: object):  # type: ignore[no-untyped-def]
    return client.post(
        "/invitations/en-masse",
        json={"invitations": lignes},
        headers=kw.get("headers", _en_tete_gestionnaire()),
    )


def test_invitations_en_masse_traitees_ligne_par_ligne() -> None:
    client = _client()
    lignes = [
        {"dossier_id": "DEMO_karim", "email": "karim@example.com"},
        {"dossier_id": "DEMO_sophie", "email": "pas-un-email"},
        {"dossier_id": "INCONNU", "email": "x@example.com"},
        {"dossier_id": "DEMO_karim", "email": "autre@example.com"},
        {"dossier_id": "DEMO_yanis", "email": "yanis@example.com"},
    ]

    corps = _en_masse(client, lignes).json()

    assert [ligne["resultat"] for ligne in corps["lignes"]] == [
        "invité",
        "email_invalide",
        "dossier_inconnu",
        "doublon_dans_le_lot",
        "invité",
    ]
    assert corps["nb_invitees"] == 2


def test_relancer_le_meme_lot_nenvoie_pas_de_seconde_invitation() -> None:
    client = _client()
    lignes = [{"dossier_id": "DEMO_karim", "email": "karim@example.com"}]
    _en_masse(client, lignes)

    corps = _en_masse(client, lignes).json()

    assert corps["lignes"][0]["resultat"] == "deja_invite"
    assert corps["nb_invitees"] == 0


def test_invitations_en_masse_refusees_sans_lien_gestionnaire() -> None:
    client = _client()
    lignes = [{"dossier_id": "DEMO_karim", "email": "karim@example.com"}]
    assert client.post("/invitations/en-masse", json={"invitations": lignes}).status_code == 401
    assert _en_masse(client, lignes, headers=_en_tete("DEMO_karim")).status_code == 403


def test_invitations_en_masse_ignorent_les_dossiers_dun_autre_portefeuille() -> None:
    """Un gestionnaire d'un autre tenant obtient « dossier_inconnu », jamais
    une invitation ni une indication que ce dossier existe ailleurs."""
    lignes = [{"dossier_id": "DEMO_karim", "email": "karim@example.com"}]

    corps = _en_masse(_client(), lignes, headers=_en_tete_gestionnaire("AUTRE_TENANT")).json()

    assert corps["lignes"][0]["resultat"] == "dossier_inconnu"


def test_un_lot_trop_gros_est_refuse() -> None:
    lignes = [{"dossier_id": f"d{i}", "email": f"{i}@example.com"} for i in range(501)]
    assert _en_masse(_client(), lignes).status_code == 422


def test_une_ecriture_contre_passee_nest_plus_a_trancher_nulle_part() -> None:
    """Bugbot, PR #11 : la paire originale + inverse ne doit revenir en revue
    ni dans la liste, ni après un justificatif, ni via une décision."""
    client = _client()
    en_tete = _en_tete("DEMO_sophie")
    url = "/dossiers/DEMO_sophie/transactions"
    ecriture_id = next(
        t["ecriture_id"]
        for t in client.get(url, headers=en_tete).json()
        if t["statut"] == "à trancher"
    )
    ledger = client.app.dependency_overrides[get_ledger]()  # type: ignore[attr-defined]
    originale = next(e for e in ledger.grand_livre("DEMO_sophie") if e.id == ecriture_id)
    ledger.enregistrer(contrepasser(originale))

    statuts = {t["ecriture_id"]: t["statut"] for t in client.get(url, headers=en_tete).json()}
    assert statuts[ecriture_id] == "validé"
    assert statuts[f"{ecriture_id}:contrepassation"] == "validé"
    justificatif = client.post(
        f"{url}/{ecriture_id}/justificatif",
        files={"fichier": ("ticket.jpg", b"contenu-photo-factice", "image/jpeg")},
        headers=en_tete,
    )
    assert justificatif.json()["statut"] == "validé"
    decision = client.post(
        f"{url}/{ecriture_id}/decision", json={"categorie": "carburant"}, headers=en_tete
    )
    assert decision.status_code == 409
