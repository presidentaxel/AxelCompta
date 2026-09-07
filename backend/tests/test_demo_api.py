"""Teste l'API démo (doc 17 §9). `get_decisions` est surchargée avec
`InMemoryDecisionRepository` (`dependency_overrides`, idiome FastAPI) : la
suite rapide vérifie le contrat HTTP sans jamais construire d'engine
Postgres — `tests/integration/test_decisions_repository.py` prouve
séparément que `PostgresDecisionRepository` respecte le même contrat.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from axelcompta.demo_api import create_app, get_decisions
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO
from axelcompta.workflow.decisions_memory import InMemoryDecisionRepository


def _client() -> TestClient:
    app = create_app()
    # Même instance à chaque requête (pas `InMemoryDecisionRepository` seul,
    # qui en recréerait une neuve — et donc vide — par requête) : une
    # décision postée doit rester visible sur les GET suivants du même
    # client, comme le fait la vraie dépendance Postgres via son engine
    # partagé.
    stub = InMemoryDecisionRepository()
    app.dependency_overrides[get_decisions] = lambda: stub
    return TestClient(app)


def test_lister_dossiers_retourne_les_3_chauffeurs_type() -> None:
    reponse = _client().get("/dossiers")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps) == 3
    assert {d["dossier_id"] for d in corps} == {p.dossier_id for p in PROFILS_DEMO}


def test_dossier_yanis_est_bien_en_franchise_et_deficitaire() -> None:
    reponse = _client().get("/dossiers/DEMO_yanis")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["tva_recettes_regime"] == "franchise"
    assert corps["resultat_cts"] < 0


def test_dossier_inconnu_retourne_404() -> None:
    reponse = _client().get("/dossiers/DEMO_inconnu")
    assert reponse.status_code == 404


def test_transactions_sophie_contiennent_des_lignes_a_trancher() -> None:
    reponse = _client().get("/dossiers/DEMO_sophie/transactions")
    assert reponse.status_code == 200
    transactions = reponse.json()
    a_trancher = [t for t in transactions if t["statut"] == "à trancher"]
    assert len(a_trancher) >= 3  # les dépenses ambiguës, doc 17 §4.2


def test_transaction_a_trancher_pointe_bien_sur_le_compte_471() -> None:
    reponse = _client().get("/dossiers/DEMO_sophie/transactions")
    a_trancher = [t for t in reponse.json() if t["statut"] == "à trancher"]
    assert all(t["compte"] == "471" for t in a_trancher)


def test_montant_settlement_est_signe_positif_cote_encaissement() -> None:
    reponse = _client().get("/dossiers/DEMO_karim/transactions")
    reglements = [t for t in reponse.json() if t["compte"] == "règlement plateforme"]
    assert reglements
    assert all(t["montant_cts"] > 0 for t in reglements)


def _premiere_a_trancher(client: TestClient, dossier_id: str) -> str:
    transactions = client.get(f"/dossiers/{dossier_id}/transactions").json()
    return next(t["ecriture_id"] for t in transactions if t["statut"] == "à trancher")


def test_trancher_en_usage_personnel_reclasse_vers_le_compte_455() -> None:
    """doc 17 §9 bloc C, doc 06 §3.6 : Sophie est EURL, donc 455."""
    client = _client()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")

    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
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
    )

    transactions = client.get("/dossiers/DEMO_sophie/transactions").json()
    ecriture = next(t for t in transactions if t["ecriture_id"] == ecriture_id)
    assert ecriture["statut"] == "validé"
    assert ecriture["compte"] == "455"


def test_trancher_diminue_le_compteur_nb_a_trancher() -> None:
    client = _client()
    avant = client.get("/dossiers/DEMO_sophie").json()["nb_a_trancher"]
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")

    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
    )

    apres = client.get("/dossiers/DEMO_sophie").json()["nb_a_trancher"]
    assert apres == avant - 1


def test_trancher_deux_fois_la_meme_ecriture_est_refuse() -> None:
    """doc 05 §5 : la décision humaine est immuable, pas de deuxième
    écriture qui l'écrase silencieusement."""
    client = _client()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
    )

    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "carburant"},
    )

    assert reponse.status_code == 409


def test_trancher_une_ecriture_deja_validee_est_refuse() -> None:
    client = _client()
    validees = [
        t
        for t in client.get("/dossiers/DEMO_karim/transactions").json()
        if t["statut"] == "validé"
    ]
    reponse = client.post(
        f"/dossiers/DEMO_karim/transactions/{validees[0]['ecriture_id']}/decision",
        json={"categorie": "usage_personnel"},
    )
    assert reponse.status_code == 409


def test_trancher_une_ecriture_inconnue_est_un_404() -> None:
    client = _client()
    reponse = client.post(
        "/dossiers/DEMO_sophie/transactions/ecriture-inconnue/decision",
        json={"categorie": "usage_personnel"},
    )
    assert reponse.status_code == 404


def test_trancher_vers_une_categorie_inconnue_est_un_400() -> None:
    client = _client()
    ecriture_id = _premiere_a_trancher(client, "DEMO_sophie")
    reponse = client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "categorie_qui_nexiste_pas"},
    )
    assert reponse.status_code == 400
