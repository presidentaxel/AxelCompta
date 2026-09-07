"""Identifiants typés — pas de `str`/`int` nu qui se mélange entre entités.

Squelette : les types existent, la génération (uuid7, ou autre stratégie à
trancher) reste à faire.
"""

from __future__ import annotations

from typing import NewType

TenantId = NewType("TenantId", str)
DossierId = NewType("DossierId", str)
EcritureId = NewType("EcritureId", str)
TransactionId = NewType("TransactionId", str)
UserId = NewType("UserId", str)  # doc 17 §9 bloc B : compte gestionnaire ou chauffeur
