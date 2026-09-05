from __future__ import annotations

from axelcompta.ingestion.providers.base import DataProvider
from axelcompta.ingestion.providers.digifactory import DigifactoryProvider
from axelcompta.ingestion.providers.file_import import FileImportProvider
from axelcompta.ingestion.providers.fixture import FixtureProvider, FixtureSettlementProvider
from axelcompta.ingestion.providers.rollee import RolleeProvider


def test_toutes_les_implementations_respectent_le_contrat_data_provider() -> None:
    for classe in (
        DigifactoryProvider,
        RolleeProvider,
        FileImportProvider,
        FixtureProvider,
        FixtureSettlementProvider,
    ):
        assert issubclass(classe, DataProvider)
        classe()  # instanciable : les 3 méthodes abstraites sont bien implémentées
