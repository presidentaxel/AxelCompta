"""Implémentation en mémoire de CompteRepository — pour les tests rapides
et pour brancher `demo_api.py` sans dépendre d'un accès réseau à Supabase
(Louis, 2026-09-07 : « je ne veux pas dépendre de Supabase pour tous les
tests »). Comme `workflow/decisions_memory.py` pour les décisions.
"""

from __future__ import annotations

from axelcompta.core.ids import DossierId

from .demo_comptes import CompteDejaInviteError, CompteRepository, Invitation, StatutInvitation


class InMemoryCompteRepository(CompteRepository):
    def __init__(self) -> None:
        self._invitations: dict[DossierId, Invitation] = {}

    def inviter(self, dossier_id: DossierId, email: str) -> Invitation:
        if dossier_id in self._invitations:
            raise CompteDejaInviteError(f"dossier déjà invité : {dossier_id}")
        invitation = Invitation(dossier_id=dossier_id, email=email, statut=StatutInvitation.INVITE)
        self._invitations[dossier_id] = invitation
        return invitation

    def statut(self, dossier_id: DossierId) -> Invitation | None:
        return self._invitations.get(dossier_id)
