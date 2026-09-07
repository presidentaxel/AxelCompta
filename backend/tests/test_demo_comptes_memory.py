from __future__ import annotations

import pytest

from axelcompta.core.ids import DossierId
from axelcompta.demo_comptes import CompteDejaInviteError, StatutInvitation
from axelcompta.demo_comptes_memory import InMemoryCompteRepository

DOSSIER = DossierId("DEMO_sophie")


def test_statut_est_none_tant_que_personne_nest_invite() -> None:
    repo = InMemoryCompteRepository()
    assert repo.statut(DOSSIER) is None


def test_inviter_cree_une_invitation_au_statut_invite() -> None:
    repo = InMemoryCompteRepository()
    invitation = repo.inviter(DOSSIER, "sophie@example.com")
    assert invitation.statut is StatutInvitation.INVITE
    assert repo.statut(DOSSIER) == invitation


def test_inviter_deux_fois_le_meme_dossier_est_refuse() -> None:
    """doc 08 §2.7 : pas de double invitation silencieuse."""
    repo = InMemoryCompteRepository()
    repo.inviter(DOSSIER, "sophie@example.com")
    with pytest.raises(CompteDejaInviteError):
        repo.inviter(DOSSIER, "sophie-bis@example.com")


def test_statut_est_isole_par_dossier() -> None:
    repo = InMemoryCompteRepository()
    autre = DossierId("DEMO_karim")
    repo.inviter(DOSSIER, "sophie@example.com")
    assert repo.statut(autre) is None
