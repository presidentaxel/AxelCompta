"""Erreurs métier typées (doc 08 §2.7) — jamais d'exception avalée, jamais de
code magique. Squelette : hiérarchie de base seulement.
"""

from __future__ import annotations


class DomaineError(Exception):
    """Racine des erreurs métier attendues (à distinguer d'un bug/invariant violé)."""


class InvariantViole(Exception):
    """Un invariant du domaine (ex. doc 06 §1) a été violé — fail-fast, jamais
    rattrapé en silence (doc 08 §5)."""
