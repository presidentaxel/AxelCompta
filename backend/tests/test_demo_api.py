"""Teste l'API démo (doc 17 §9 semaine 2). Lecture seule pour l'instant."""

from __future__ import annotations

from fastapi.testclient import TestClient

from axelcompta.demo_api import app
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO

client = TestClient(app)


def test_lister_dossiers_retourne_les_3_chauffeurs_type() -> None:
    reponse = client.get("/dossiers")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps) == 3
    assert {d["dossier_id"] for d in corps} == {p.dossier_id for p in PROFILS_DEMO}


def test_dossier_yanis_est_bien_en_franchise_et_deficitaire() -> None:
    reponse = client.get("/dossiers/DEMO_yanis")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["tva_recettes_regime"] == "franchise"
    assert corps["resultat_cts"] < 0


def test_dossier_inconnu_retourne_404() -> None:
    reponse = client.get("/dossiers/DEMO_inconnu")
    assert reponse.status_code == 404


def test_transactions_sophie_contiennent_des_lignes_a_trancher() -> None:
    reponse = client.get("/dossiers/DEMO_sophie/transactions")
    assert reponse.status_code == 200
    transactions = reponse.json()
    a_trancher = [t for t in transactions if t["statut"] == "à trancher"]
    assert len(a_trancher) >= 3  # les dépenses ambiguës, doc 17 §4.2


def test_transaction_a_trancher_pointe_bien_sur_le_compte_471() -> None:
    reponse = client.get("/dossiers/DEMO_sophie/transactions")
    a_trancher = [t for t in reponse.json() if t["statut"] == "à trancher"]
    assert all(t["compte"] == "471" for t in a_trancher)


def test_montant_settlement_est_signe_positif_cote_encaissement() -> None:
    reponse = client.get("/dossiers/DEMO_karim/transactions")
    reglements = [t for t in reponse.json() if t["compte"] == "règlement plateforme"]
    assert reglements
    assert all(t["montant_cts"] > 0 for t in reglements)
