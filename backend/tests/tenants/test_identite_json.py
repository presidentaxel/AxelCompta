from __future__ import annotations

import json

from axelcompta.demo_identites import IDENTITE_SOPHIE
from axelcompta.tenants.identite_json import identite_depuis_json, identite_vers_json


def test_aller_retour_json_sans_perte() -> None:
    donnees = identite_vers_json(IDENTITE_SOPHIE)
    # Passe par du vrai JSON, comme la colonne Postgres.
    relu = identite_depuis_json(json.loads(json.dumps(donnees)))
    assert relu == IDENTITE_SOPHIE


def test_absence_d_identite() -> None:
    assert identite_vers_json(None) is None
    assert identite_depuis_json(None) is None
