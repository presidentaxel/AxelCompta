"""Teste le stockage des justificatifs de démo (doc 17 §9 Semaine 3,
doc 19 §5.7) — deux implémentations, même contrat (doc 18)."""

from __future__ import annotations

from pathlib import Path

import pytest

from axelcompta.demo_justificatifs import (
    FichierJustificatifRepository,
    InMemoryJustificatifRepository,
    JustificatifRepository,
)


@pytest.fixture(params=["memoire", "fichier"])
def repo(request: pytest.FixtureRequest, tmp_path: Path) -> JustificatifRepository:
    if request.param == "memoire":
        return InMemoryJustificatifRepository()
    return FichierJustificatifRepository(tmp_path)


def test_aucun_justificatif_au_depart(repo: JustificatifRepository) -> None:
    assert repo.a_un_justificatif("DEMO_karim", "ecriture-1") is False


def test_enregistrer_rend_a_un_justificatif_vrai(repo: JustificatifRepository) -> None:
    repo.enregistrer("DEMO_karim", "ecriture-1", b"contenu-photo", ".jpg")
    assert repo.a_un_justificatif("DEMO_karim", "ecriture-1") is True


def test_une_autre_ecriture_reste_sans_justificatif(repo: JustificatifRepository) -> None:
    repo.enregistrer("DEMO_karim", "ecriture-1", b"contenu-photo", ".jpg")
    assert repo.a_un_justificatif("DEMO_karim", "ecriture-2") is False


def test_un_autre_dossier_reste_sans_justificatif(repo: JustificatifRepository) -> None:
    """Même ecriture_id, dossier différent — pas de collision entre dossiers."""
    repo.enregistrer("DEMO_karim", "ecriture-1", b"contenu-photo", ".jpg")
    assert repo.a_un_justificatif("DEMO_sophie", "ecriture-1") is False


def test_fichier_repository_ecrit_vraiment_sur_disque(tmp_path: Path) -> None:
    """Spécifique à l'implémentation fichier : preuve que le contenu est
    vraiment écrit, pas juste marqué en mémoire."""
    repo = FichierJustificatifRepository(tmp_path)
    repo.enregistrer("DEMO_karim", "ecriture-1", b"contenu-photo", ".jpg")
    chemin = tmp_path / "DEMO_karim" / "ecriture-1.jpg"
    assert chemin.read_bytes() == b"contenu-photo"
