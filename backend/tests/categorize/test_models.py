from __future__ import annotations

from axelcompta.categorize.models import Etage, ProposedEntry
from axelcompta.core.ids import DossierId, TransactionId


def test_proposed_entry_porte_letage_qui_la_produit() -> None:
    proposition = ProposedEntry(
        dossier_id=DossierId("d1"),
        transaction_id=TransactionId("tx1"),
        categorie="carburant",
        etage=Etage.REGLE,
        confiance=0.95,
    )
    assert proposition.etage is Etage.REGLE
    assert 0.0 <= proposition.confiance <= 1.0


def test_les_4_etages_du_pipeline_existent() -> None:
    assert {e.name for e in Etage} == {"REGLE", "ML", "LLM", "REVUE_HUMAINE"}
