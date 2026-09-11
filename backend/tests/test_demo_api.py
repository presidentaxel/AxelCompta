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

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import axelcompta.demo_auth as demo_auth
from axelcompta.core.ids import DossierId, EcritureId
from axelcompta.demo_api import (
    create_app,
    get_comptes,
    get_decisions,
    get_justificatifs,
    get_signatures_inpi,
)
from axelcompta.demo_comptes_memory import InMemoryCompteRepository
from axelcompta.demo_justificatifs import InMemoryJustificatifRepository
from axelcompta.ingestion.providers.chauffeurs_demo import PROFILS_DEMO
from axelcompta.workflow.decisions_memory import InMemoryDecisionRepository
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
        "user_metadata": {"dossier_id": dossier_id},
    }
    return jwt.encode(charge_utile, _CLE_PRIVEE_TEST, algorithm="ES256")


def _en_tete(dossier_id: str) -> dict[str, str]:
    """doc 19 §8bis : jeton indiv valide, scopé sur `dossier_id`."""
    return {"Authorization": f"Bearer {_jeton_chauffeur(dossier_id)}"}


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


def _client_et_stubs() -> tuple[
    TestClient, InMemoryDecisionRepository, InMemoryJustificatifRepository
]:
    app = create_app()
    # Même instance à chaque requête (pas juste la classe : une nouvelle
    # instance par requête serait vide à chaque fois) — une décision ou une
    # invitation doit rester visible sur les GET suivants du même client,
    # comme le font les vraies dépendances via leur connexion partagée.
    decisions_stub = InMemoryDecisionRepository()
    comptes_stub = InMemoryCompteRepository()
    justificatifs_stub = InMemoryJustificatifRepository()
    # `get_signatures_inpi` retourne par défaut un singleton de niveau
    # module (demo_api.py) — surchargé ici pour isoler chaque test, sinon
    # une signature posée par un test resterait visible dans les suivants.
    signatures_stub = InMemorySignatureRepository()
    app.dependency_overrides[get_decisions] = lambda: decisions_stub
    app.dependency_overrides[get_comptes] = lambda: comptes_stub
    app.dependency_overrides[get_justificatifs] = lambda: justificatifs_stub
    app.dependency_overrides[get_signatures_inpi] = lambda: signatures_stub
    return TestClient(app), decisions_stub, justificatifs_stub


def _client() -> TestClient:
    return _client_et_stubs()[0]


def test_lister_dossiers_retourne_les_3_chauffeurs_type() -> None:
    reponse = _client().get("/dossiers")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps) == 3
    assert {d["dossier_id"] for d in corps} == {p.dossier_id for p in PROFILS_DEMO}


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
    """doc 19 §6 : action gestionnaire, toujours sans login — pas de jeton
    ici, contrairement aux routes de niveau dossier ci-dessus."""
    client = _client()
    reponse = client.post("/dossiers/DEMO_karim/inviter", json={"email": "karim@example.com"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps == {"dossier_id": "DEMO_karim", "email": "karim@example.com", "statut": "invité"}


def test_inviter_est_reflete_par_un_get_ulterieur() -> None:
    """doc 19 §3.2 : le statut d'invitation doit apparaître au dashboard,
    pas seulement dans la réponse du POST."""
    client = _client()
    client.post("/dossiers/DEMO_karim/inviter", json={"email": "karim@example.com"})

    reponse = client.get("/dossiers/DEMO_karim", headers=_en_tete("DEMO_karim"))

    assert reponse.json()["statut_invitation"] == "invité"


def test_inviter_deux_fois_le_meme_dossier_est_refuse() -> None:
    client = _client()
    client.post("/dossiers/DEMO_karim/inviter", json={"email": "karim@example.com"})

    reponse = client.post("/dossiers/DEMO_karim/inviter", json={"email": "autre@example.com"})

    assert reponse.status_code == 409


def test_karim_est_en_mode_chauffeur_direct_les_autres_en_gestionnaire() -> None:
    """doc 19 §4 : les deux modes doivent être représentés dans la démo."""
    corps = {p["dossier_id"]: p for p in _client().get("/dossiers").json()}
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
    assert "455" not in avant

    client.post(
        f"/dossiers/DEMO_sophie/transactions/{ecriture_id}/decision",
        json={"categorie": "usage_personnel"},
        headers=en_tete,
    )

    apres = client.get("/dossiers/DEMO_sophie/fec.txt", headers=en_tete).text
    assert "455" in apres


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
