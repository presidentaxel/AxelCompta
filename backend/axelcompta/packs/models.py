"""Squelette de structure. Le chargement réel du pack VTC depuis
`_AUDIT_DONNEES/packs_vtc/` (taxonomie, règles regex, mapping PCG) reste à
écrire — voir packs/README.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Pack:
    """Un pack métier : taxonomie + règles système + templates d'écritures."""

    secteur: str  # ex. "vtc"
    version: str
    categories: tuple[str, ...] = field(default_factory=tuple)
