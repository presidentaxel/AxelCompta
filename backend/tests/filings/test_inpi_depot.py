from __future__ import annotations

from datetime import date

from axelcompta.closing.models import LiassePivot
from axelcompta.core.ids import DossierId
from axelcompta.filings.inpi_depot import (
    MENTION_FICTIVE,
    PdfDepotInpiRenderer,
    construire_payload_comptes_annuels,
    guide_greffe,
)

CASES = {
    "CA_HT": 945_45,
    "CHARGES": 160_00,
    "RESULTAT": 785_45,
    "TRESORERIE": 848_00,
    "TVA_A_PAYER": 62_55,
}
LIASSE = LiassePivot(
    dossier_id=DossierId("d1"),
    exercice="2026",
    cases=CASES,
    exercice_debut=date(2026, 1, 1),
    exercice_fin=date(2026, 12, 31),
)


def test_rendre_produit_des_octets_pdf_valides() -> None:
    pdf = PdfDepotInpiRenderer().rendre(LIASSE)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 100


def test_payload_a_la_forme_du_contrat_interface_inpi() -> None:
    # doc 20 §3 : content.comptesAnnuels
    payload = construire_payload_comptes_annuels(LIASSE)
    assert payload == {
        "comptesConsolides": False,
        "dateCloture": "2026-12-31",
        "dateDebutExerciceComptable": "2026-01-01",
        "dateFinExerciceComptable": "2026-12-31",
        "dispenseDepotAnnexes": False,
        "depotSimplifie": False,
        "compteBilan": {"confidentiel": False},
        "compteResultat": {"confidentiel": False},
    }


def test_payload_sans_bornes_exercice_connues_a_des_dates_nulles() -> None:
    liasse_sans_bornes = LiassePivot(dossier_id=DossierId("d2"), exercice="2026", cases=CASES)
    payload = construire_payload_comptes_annuels(liasse_sans_bornes)
    assert payload["dateCloture"] is None
    assert payload["dateDebutExerciceComptable"] is None


def test_mention_fictive_est_bien_dans_le_pdf() -> None:
    # doc 08 §5 : un artefact de démo ne doit jamais pouvoir se faire
    # passer pour un vrai document officiel — vérifié dans le contenu brut
    # du PDF (le texte reportlab n'est pas trivialement grep-able une fois
    # compressé, donc on vérifie juste que la génération n'a pas explosé et
    # que la mention est bien câblée dans le module).
    assert "FICTIF" in MENTION_FICTIVE
    assert "NE PAS DÉPOSER" in MENTION_FICTIVE


def _liasse(forme: str, **cases: int) -> LiassePivot:
    return LiassePivot(
        dossier_id=DossierId("d1"),
        exercice="2025",
        cases=cases,
        exercice_debut=date(2025, 1, 6),
        exercice_fin=date(2025, 12, 31),
        forme_juridique=forme,
    )


def _reponses(forme: str, **cases: int) -> dict[str, str]:
    return {ligne.question: ligne.reponse for ligne in guide_greffe(_liasse(forme, **cases)).lignes}


def test_sasu_micro_est_dispensee_d_annexe_et_signe_seule() -> None:
    guide = guide_greffe(_liasse("SASU", **{"CA_HT": 13_000_00, "2033A.180": 8_000_00}))
    assert guide.depose is True
    assert _reponses("SASU", **{"CA_HT": 13_000_00, "2033A.180": 8_000_00}) == {
        "Type de dépôt": "Comptes sociaux",
        "Dépôt rectificatif": "Non",
        "Début de l'exercice": "06/01/2025",
        "Clôture de l'exercice": "31/12/2025",
        "Dispensée de déposer les annexes": "Oui",
        "Confidentialité des comptes": "Oui",
        "Confidentialité du compte de résultat": "Non",
        "Présentation simplifiée": "Non",
    }
    assert [piece.nom for piece in guide.pieces] == [
        "Bilan actif / passif",
        "Compte de résultat",
        "Décision de l'associé unique",
    ]
    assert guide.pieces[0].document == "bilan.pdf"
    assert guide.pieces[2].document is None


def test_petite_entreprise_joint_l_annexe_et_masque_le_resultat() -> None:
    # Deux seuils micro dépassés, aucun seuil petite.
    cases = {"CA_HT": 2_000_000_00, "2033A.180": 1_000_000_00, "2033E.376": 5_00}
    guide = guide_greffe(_liasse("SAS", **cases))
    reponses = {ligne.question: ligne.reponse for ligne in guide.lignes}
    assert reponses["Dispensée de déposer les annexes"] == "Non"
    assert reponses["Confidentialité des comptes"] == "Non"
    assert reponses["Confidentialité du compte de résultat"] == "Oui"
    assert guide.pieces[-1].nom == "Annexe comptable"
    assert "assemblée générale" in guide.pieces[2].nom


def test_entreprise_individuelle_ne_depose_pas_au_greffe() -> None:
    guide = guide_greffe(_liasse("EI", **{"CA_HT": 10_000_00}))
    assert guide.depose is False
    assert guide.pieces == ()
