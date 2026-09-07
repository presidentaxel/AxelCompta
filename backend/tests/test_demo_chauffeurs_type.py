"""Teste la démo produit sur 3 chauffeurs type (doc 17 §4, pivot 2026-09-06).

Contrairement à `test_demo_multi_dossiers.py`, aucun skip conditionnel :
`chauffeurs_demo.py` ne dépend d'aucun fichier gitignored, cette démo tourne
donc sur n'importe quel clone du repo.
"""

from __future__ import annotations

from pathlib import Path

from axelcompta.demo_chauffeurs_type import PROFILS_DEMO, construire_ledger, executer


def test_construire_ledger_ne_leve_aucune_ecriture_desequilibree() -> None:
    """`InMemoryLedgerService.enregistrer` vérifie l'équilibre à chaque
    écriture (doc 06 §1) — si cette fonction ne lève pas, tout le pipeline
    (settlement + reste des transactions) est équilibré pour les 3 profils."""
    for profil in PROFILS_DEMO:
        ledger, _propositions = construire_ledger(profil)
        assert len(ledger.grand_livre(profil.dossier_id)) > 0


def test_karim_a_bien_un_settlement_non_reconcilie_traite_en_mode_degrade() -> None:
    """doc 13 §4.3/§6 : le règlement retardé de Karim ne produit pas
    d'écriture ventilée TVA (settlement non réconcilié, ignoré comme les
    autres), mais son virement bancaire, lui, existe toujours et doit être
    catégorisé (mode dégradé — 706 brut, sans ventilation)."""
    profil = next(p for p in PROFILS_DEMO if p.nom == "Karim")
    ledger, _propositions = construire_ledger(profil)
    libelles_706 = [
        ecriture.libelle
        for ecriture in ledger.grand_livre(profil.dossier_id)
        if any(ligne.compte == "706" for ligne in ecriture.lignes)
    ]
    assert any("uber" in libelle.lower() for libelle in libelles_706)


def test_sophie_a_une_ecriture_en_attente_pour_la_depense_ambigue() -> None:
    """doc 17 §11 : pas d'auto-acceptation sur la dépense Zara — doit
    atterrir sur le compte d'attente 471, pas un compte de résultat."""
    profil = next(p for p in PROFILS_DEMO if p.nom == "Sophie")
    ledger, _propositions = construire_ledger(profil)
    comptes_touches = {
        ligne.compte
        for ecriture in ledger.grand_livre(profil.dossier_id)
        for ligne in ecriture.lignes
    }
    assert "471" in comptes_touches


def test_executer_produit_un_rapport_et_les_fichiers_par_chauffeur(tmp_path: Path) -> None:
    chemin_rapport = executer(tmp_path)
    assert chemin_rapport == tmp_path / "rapport.html"
    rapport = chemin_rapport.read_text(encoding="utf-8")

    for profil in PROFILS_DEMO:
        assert profil.nom in rapport
        assert profil.dossier_id in rapport
        dossier_sortie = tmp_path / profil.dossier_id
        assert (dossier_sortie / "liasse.pdf").read_bytes().startswith(b"%PDF-")
        assert (dossier_sortie / "cerfa_2065.pdf").read_bytes().startswith(b"%PDF-")
        assert (
            (dossier_sortie / "journal.fec.txt")
            .read_text(encoding="utf-8")
            .startswith("JournalCode\t")
        )
        assert (dossier_sortie / "balance.csv").is_file()
