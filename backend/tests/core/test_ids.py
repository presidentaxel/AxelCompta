from __future__ import annotations

from axelcompta.core.ids import DossierId, EcritureId, TenantId, TransactionId


def test_les_ids_typés_restent_des_str_a_lexecution() -> None:
    # NewType ne fait aucune vérification à l'exécution : le typage n'existe
    # que pour mypy. Ce test documente ce fait plutôt que de le tester en vrai.
    assert TenantId("t1") == "t1"
    assert DossierId("d1") == "d1"
    assert EcritureId("e1") == "e1"
    assert TransactionId("tx1") == "tx1"
